import base64
import json
import struct
import time
import traceback
from typing import Any, Dict, List, Optional

import aiohttp
import base58
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator
from solana.constants import LAMPORTS_PER_SOL
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Finalized
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.message import Message, MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction, VersionedTransaction
from spl.token._layouts import ACCOUNT_LAYOUT, INSTRUCTIONS_LAYOUT, MINT_LAYOUT
from spl.token.constants import (
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
)
from spl.token.core import MintInfo
from spl.token.instructions import (
    TransferCheckedParams,
    create_associated_token_account,
    decode_transfer_checked,
    get_associated_token_address,
    transfer_checked,
)

from schemas.token_schemas import (
    MintTokenSchema,
    TokenAccountCreationSchema,
    TokenAccountSchema,
    TokenMetaDataSchema,
    TransferTokenCreationSchema,
)
from schemas.transaction_schemas import TransactionRetrieverSchema, TransactionSchema
from schemas.wallet_schemas import WalletModelCreationSchema, WalletModelSchema
from services.solana_transaction_classifier import SolanaTransactionClassifier

METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")


class SolanaService:
    def __init__(self, endpoint="https://api.devnet.solana.com"):
        self.endpoint = endpoint

    def sol_to_lamports(self, sol_amount: float) -> int:
        return int(sol_amount * LAMPORTS_PER_SOL)

    def lamports_to_sol(self, lamports: int) -> float:
        return lamports / LAMPORTS_PER_SOL

    def create_keypair_from_seed_bytes(self, seed_bytes: bytes) -> Keypair:
        return Keypair.from_seed(seed_bytes[:32])

    def create_keypair_from_private_key(self, private_key: str) -> Keypair | None:
        try:
            secret_key_bytes = bytes(json.loads(private_key))
            return Keypair.from_bytes(secret_key_bytes)
        except ValueError as e:
            print(f"Failed to parse secret key: {e}")
            return None

    def create_keypair_from_base58_private_key(
        self, base58_private_key: str
    ) -> Keypair | None:
        try:
            print(
                f"create_keypair_from_base58_private_key(self, base58_private_key: {base58_private_key})"
            )
            secret_key_bytes = bytes(base58.b58decode(base58_private_key))
            return Keypair.from_bytes(secret_key_bytes)
        except Exception as e:
            print(f"Invalid base58 private key: {e}")
            return None

    def _get_sender_pubkey_str(self, owner_bs58_private_key: str) -> str:
        if not owner_bs58_private_key:
            return ""
        try:
            keypair = self.create_keypair_from_base58_private_key(
                owner_bs58_private_key
            )
            return str(keypair.pubkey()) if keypair else ""
        except Exception:
            return ""

    async def airdrop(self, address: str, amount: float = 5.0) -> WalletModelSchema:
        async with AsyncClient(
            self.endpoint,
            timeout=30.0,
        ) as client:
            try:
                pubkey = Pubkey.from_string(address)
                res = await client.request_airdrop(pubkey, self.sol_to_lamports(amount))
                print(f"Airdrop signature: {res.value}")
                new_balance = await client.get_balance(pubkey)
                return WalletModelSchema(
                    address=address,
                    balance=self.lamports_to_sol(new_balance.value),
                    signature=str(res.value),
                )
            except Exception as e:
                new_balance = await client.get_balance(pubkey)
                return WalletModelSchema(
                    balance=self.lamports_to_sol(new_balance.value),
                    error=f"{e if (str(e) or "").strip() else 'Cannot airdrop now. Please try again.'}",
                )

    async def get_balance(self, address: str) -> float:
        async with AsyncClient(
            self.endpoint,
            timeout=30.0,
        ) as client:
            pubkey = Pubkey.from_string(address)
            response = await client.get_balance(pubkey)
            lamports = response.value
            return self.lamports_to_sol(lamports)

    async def get_token_accounts(self, owner_address: str):
        async with AsyncClient(
            self.endpoint,
            timeout=30.0,
        ) as client:
            owner = Pubkey.from_string(owner_address)
            result = await client.get_token_accounts_by_owner_json_parsed(
                owner, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
            )
            accounts = [acc.account.data.parsed for acc in result.value]
            json_data = json.dumps(accounts, indent=2)
            return json_data

    def _create_wallet_model_from_keypair(
        self, keypair: Keypair, mnemonics: str | None = None
    ) -> WalletModelSchema:
        try:
            secret_bytes = bytes(keypair)
            return WalletModelSchema(
                bs58PrivateKey=base58.b58encode(secret_bytes).decode(),
                privateKey=str(list[int](secret_bytes)),
                address=str(keypair.pubkey()),
                mnemonics=mnemonics,
                balance=0,
            )
        except Exception as e:
            return WalletModelSchema(
                error=f"Cannot create wallet model from keypair: {e}"
            )

    def _restore_wallet_from_mnemonic(self, mnemonic: str) -> WalletModelSchema:
        try:
            seed_bytes = Bip39SeedGenerator(mnemonic).Generate("optional-passphrase")
            keypair = self.create_keypair_from_seed_bytes(seed_bytes)
            return self._create_wallet_model_from_keypair(keypair, mnemonic)
        except Exception as e:
            error_msg = (
                "Failed to parse mnemonic: Invalid mnemonic checksum."
                if "Invalid checksum" in str(e)
                else f"Failed to parse mnemonic: {e}"
            )
            return WalletModelSchema(error=error_msg)

    def _restore_wallet_from_private_key(self, private_key: str) -> WalletModelSchema:
        try:
            keypair = self.create_keypair_from_private_key(private_key=private_key)
            if not keypair:
                raise ValueError("Cannot create keypair from the private key.")
            return self._create_wallet_model_from_keypair(keypair)
        except ValueError as e:
            print(f"Failed to parse secret key: {e}")
            return WalletModelSchema(error=f"Failed to parse secret key: {e}")

    def _restore_wallet_from_bs58_key(self, bs58_private_key: str) -> WalletModelSchema:
        try:
            keypair = Keypair.from_base58_string(bs58_private_key)
            if keypair is None:
                raise ValueError("Failed to parse bs58 private key.")
            return self._create_wallet_model_from_keypair(keypair)
        except Exception as e:
            print(f"Failed to parse bs58 private key: {e}")
            return WalletModelSchema(error=str(e))

    def _create_new_wallet(self) -> WalletModelSchema:
        generated_mnemonic = Bip39MnemonicGenerator().FromWordsNumber(24)
        seed_bytes = Bip39SeedGenerator(generated_mnemonic).Generate(
            "optional-passphrase"
        )
        keypair = self.create_keypair_from_seed_bytes(seed_bytes)
        return self._create_wallet_model_from_keypair(keypair, str(generated_mnemonic))

    async def create_or_restore_wallet(
        self,
        data: WalletModelCreationSchema,
    ) -> WalletModelSchema:
        mnemonic = (data.mnemonics or "").strip()
        private_key = (data.privateKey or "").strip()
        bs58_private_key = (data.bs58PrivateKey or "").strip()

        if mnemonic:
            return self._restore_wallet_from_mnemonic(mnemonic)
        elif private_key:
            return self._restore_wallet_from_private_key(private_key)
        elif bs58_private_key:
            return self._restore_wallet_from_bs58_key(bs58_private_key)
        else:
            return self._create_new_wallet()

    async def get_mint_token(self, mint_address: str) -> MintTokenSchema:
        async with AsyncClient(
            self.endpoint,
            timeout=30.0,
        ) as client:
            try:
                print(f"get_mint_token(self, mint_address: {mint_address})")

                mint_address_key = Pubkey.from_string(mint_address)

                # Get account info
                account_info = await client.get_account_info(mint_address_key)
                # Parse mint data using layout
                mint_data = MINT_LAYOUT.parse(account_info.value.data)

                # Create MintInfo object
                mint_info = MintInfo(
                    mint_authority=mint_data.mint_authority,
                    supply=mint_data.supply,
                    decimals=mint_data.decimals,
                    is_initialized=mint_data.is_initialized,
                    freeze_authority=mint_data.freeze_authority,
                )

                authority_keypair = Pubkey.from_bytes(mint_info.mint_authority)
                # freeze_authority_keypair
                _ = Pubkey.from_bytes(mint_info.freeze_authority)

                # fetch token meta data
                token_meta_data = await self.get_token_metadata(client, mint_address)

                meta_data_from_uri = await self.fetch_token_metadata_from_uri(
                    token_meta_data.uri
                )

                return MintTokenSchema(
                    address=mint_address,
                    decimals=mint_info.decimals,
                    supply=mint_info.supply,
                    is_initialized=mint_info.is_initialized,
                    mint_authority=str(authority_keypair),
                    update_authority=token_meta_data.update_authority,
                    name=token_meta_data.name,
                    symbol=token_meta_data.symbol,
                    uri=token_meta_data.uri,
                    logo=meta_data_from_uri.get("image"),
                    is_mutable=token_meta_data.is_mutable,
                )
            except Exception as e:
                print(f"Get mint token info from Solana is error: {e}")
                return MintTokenSchema(error=f"Solana return: {e}")

    def validate_public_key(self, wallet_address: str) -> bool:
        key = Pubkey.from_string(wallet_address)
        return key.is_on_curve()

    async def _prepare_sol_transfer_information(
        self,
        sender_base58_private_key: str,
        recipient_address: str,
        amount: float,
        client: AsyncClient,
    ):
        sender = self.create_keypair_from_base58_private_key(sender_base58_private_key)
        recipient = Pubkey.from_string(recipient_address)
        transfer_amount = self.sol_to_lamports(amount)
        latest_blockhash = await client.get_latest_blockhash()
        transfer_instruction = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient,
                lamports=transfer_amount,
            )
        )
        message = MessageV0.try_compile(
            payer=sender.pubkey(),
            instructions=[transfer_instruction],
            address_lookup_table_accounts=[],
            recent_blockhash=latest_blockhash.value.blockhash,
        )
        return sender, transfer_amount, message

    async def _prepare_sol_transfer(
        self,
        data: TransferTokenCreationSchema,
        client: AsyncClient,
    ):
        sender_base58_private_key = data.owner_bs58_private_key
        recipient_address = data.recipient
        amount = data.amount

        sender, transfer_amount, message = await self._prepare_sol_transfer_information(
            sender_base58_private_key, recipient_address, amount, client
        )

        fee_response = await client.get_fee_for_message(message)
        fee_lamports = fee_response.value
        fee_sol = self.lamports_to_sol(fee_lamports)

        return sender, transfer_amount, message, fee_lamports, fee_sol

    async def prepare_to_transfer_sol(
        self,
        data: TransferTokenCreationSchema,
    ) -> TransactionSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            try:
                sender, _, _, fee_lamports, fee_sol = await self._prepare_sol_transfer(
                    data, client
                )

                return TransactionSchema(
                    sender=str(sender.pubkey()),
                    recipient=data.recipient,
                    amount=data.amount,
                    fee_lamports=fee_lamports,
                    fee_sol=fee_sol,
                    status="prepared",
                )
            except Exception as e:
                sender_pubkey_str = self._get_sender_pubkey_str(
                    data.owner_bs58_private_key
                )
                return TransactionSchema(
                    sender=sender_pubkey_str,
                    recipient=data.recipient,
                    amount=data.amount,
                    status=str(e),
                )

    async def send_sol(
        self,
        data: TransferTokenCreationSchema,
    ) -> TransactionSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            signature = None
            try:
                (
                    sender,
                    transfer_amount,
                    message,
                    fee_lamports,
                    fee_sol,
                ) = await self._prepare_sol_transfer(data, client)

                transaction = VersionedTransaction(message, [sender])
                send_response = await client.send_transaction(transaction)
                signature = send_response.value

                # Wait for confirmation
                confirmation = await client.confirm_transaction(
                    signature,
                    commitment=Confirmed,
                )

                print(f"Transaction confirmed: {confirmation.value}")

                # Verify the transaction was successful
                if confirmation.value[0].err is None:
                    print("Transaction successful!")
                    return TransactionSchema(
                        sender=str(sender.pubkey()),
                        recipient=data.recipient,
                        signature=str(signature),
                        status="confirmed",
                        amount=data.amount,
                        total_sol=data.amount + fee_sol,
                        total_lamports=transfer_amount + fee_lamports,
                        fee_sol=fee_sol,
                        fee_lamports=fee_lamports,
                        token="Solana",
                        symbol="SOL",
                        direction="out",
                        timestamp=int(time.time()),
                    )
                else:
                    print(f"Transaction failed: {confirmation.value[0].err}")
                    return TransactionSchema(
                        sender=str(sender.pubkey()),
                        recipient=data.recipient,
                        signature=str(signature),
                        status="failed",
                        amount=data.amount,
                        token="Solana",
                        symbol="SOL",
                        direction="out",
                        timestamp=int(time.time()),
                        error=str(confirmation.value[0].err),
                    )

            except Exception as e:
                sender_pubkey_str = self._get_sender_pubkey_str(
                    data.owner_bs58_private_key
                )
                return TransactionSchema(
                    sender=sender_pubkey_str,
                    recipient=data.recipient,
                    signature=str(signature) if signature else None,
                    status="failed",
                    amount=data.amount,
                    token="Solana",
                    symbol="SOL",
                    direction="out",
                    timestamp=int(time.time()),
                    error=str(e),
                )

    def _get_spl_transfer_parties(self, data: TransferTokenCreationSchema):
        owner = self.create_keypair_from_base58_private_key(data.owner_bs58_private_key)
        payer = (
            self.create_keypair_from_base58_private_key(data.payer_bs58_private_key)
            if data.payer_bs58_private_key
            else owner
        )
        receiver = Pubkey.from_string(data.recipient)
        mint_address = Pubkey.from_string(data.mint_address)

        source_token_account = get_associated_token_address(
            owner=owner.pubkey(),
            mint=mint_address,
        )
        destination_token_account = get_associated_token_address(
            owner=receiver,
            mint=mint_address,
        )
        return (
            owner,
            payer,
            receiver,
            mint_address,
            source_token_account,
            destination_token_account,
        )

    async def prepare_to_transfer_spl_tokens(
        self, data: TransferTokenCreationSchema
    ) -> TransactionSchema:
        try:
            async with AsyncClient(self.endpoint, timeout=30.0) as client:
                (
                    owner,
                    payer,
                    receiver,
                    mint_address,
                    source_token_account,
                    destination_token_account,
                ) = self._get_spl_transfer_parties(data)

                decimals = data.decimals
                amount_to_transfer = int(data.amount * (10**decimals))

                recent_blockhash = await client.get_latest_blockhash()

                token_account_creation_fee_lamports = 0
                required_for_dest_token_account_creation_fee = False

                existing_account = await client.get_account_info(
                    destination_token_account
                )
                if not existing_account.value:
                    required_for_dest_token_account_creation_fee = True
                    token_account_creation_inst = create_associated_token_account(
                        payer=payer.pubkey(),
                        owner=receiver,
                        mint=mint_address,
                    )

                    token_account_creation_msg = Message.new_with_blockhash(
                        instructions=[token_account_creation_inst],
                        payer=payer.pubkey(),
                        blockhash=recent_blockhash.value.blockhash,
                    )
                    fee_response = await client.get_fee_for_message(
                        token_account_creation_msg
                    )
                    token_account_creation_fee_lamports = fee_response.value

                transfer_instruction = transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=source_token_account,
                        mint=mint_address,
                        dest=destination_token_account,
                        owner=owner.pubkey(),
                        amount=amount_to_transfer,
                        decimals=decimals,
                    )
                )

                message = MessageV0.try_compile(
                    payer=payer.pubkey(),
                    instructions=[transfer_instruction],
                    address_lookup_table_accounts=[],
                    recent_blockhash=recent_blockhash.value.blockhash,
                )

                fee_response = await client.get_fee_for_message(message)
                fee_lamports = fee_response.value
                fee_sol = self.lamports_to_sol(fee_lamports)
                token_account_creation_fee_sol = self.lamports_to_sol(
                    token_account_creation_fee_lamports
                )

                return TransactionSchema(
                    sender=str(owner.pubkey()),
                    payer=str(payer.pubkey()),
                    recipient=str(receiver),
                    source=str(source_token_account),
                    destination=str(destination_token_account),
                    status="prepared",
                    latest_blockhash=str(recent_blockhash.value.blockhash),
                    amount=data.amount,
                    fee_sol=fee_sol,
                    fee_lamports=fee_lamports,
                    token_account_creation_fee_sol=token_account_creation_fee_sol,
                    token_account_creation_fee_lamports=token_account_creation_fee_lamports,
                    direction="out",
                    required_for_dest_token_account_creation_fee=required_for_dest_token_account_creation_fee,
                )
        except Exception as e:
            sender_pubkey_str = self._get_sender_pubkey_str(data.owner_bs58_private_key)
            return TransactionSchema(
                sender=sender_pubkey_str,
                recipient=data.recipient,
                amount=data.amount,
                status="failed",
                error=str(e),
            )

    async def send_tokens(self, data: TransferTokenCreationSchema):
        signature = None
        try:
            async with AsyncClient(self.endpoint, timeout=30.0) as client:
                (
                    owner,
                    payer,
                    receiver,
                    mint_address,
                    source_token_account,
                    destination_token_account,
                ) = self._get_spl_transfer_parties(data)

                decimals = data.decimals
                amount_to_transfer = int(data.amount * (10**decimals))

                recent_blockhash = await client.get_latest_blockhash()

                instructions = []

                existing_account = await client.get_account_info(
                    destination_token_account
                )
                if not existing_account.value:
                    if not data.pay_for_patner_token_account_creation:
                        return TransactionSchema(
                            error="Destination token account does not exist. And `pay_for_patner_token_account_creation` is false."
                        )

                    token_account_creation_instruction = (
                        create_associated_token_account(
                            payer=payer.pubkey(),
                            owner=receiver,
                            mint=mint_address,
                        )
                    )
                    instructions.append(token_account_creation_instruction)

                transfer_checking = transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=source_token_account,
                        mint=mint_address,
                        dest=destination_token_account,
                        owner=owner.pubkey(),
                        amount=amount_to_transfer,
                        decimals=decimals,
                    )
                )
                instructions.append(transfer_checking)

                message = MessageV0.try_compile(
                    payer=payer.pubkey(),
                    instructions=instructions,
                    address_lookup_table_accounts=[],
                    recent_blockhash=recent_blockhash.value.blockhash,
                )

                signers = [owner]
                if payer.pubkey() != owner.pubkey():
                    signers.append(payer)

                transaction = VersionedTransaction(message, signers)

                send_response = await client.send_transaction(transaction)
                signature = send_response.value

                # Confirm transaction
                confirmation = await client.confirm_transaction(
                    signature, commitment=Confirmed, sleep_seconds=1
                )

                if confirmation.value and confirmation.value[0].err is None:
                    fee_response = await client.get_fee_for_message(message)
                    fee_lamports = fee_response.value
                    fee_sol = self.lamports_to_sol(fee_lamports)

                    return TransactionSchema(
                        sender=str(owner.pubkey()),
                        payer=str(payer.pubkey()),
                        recipient=str(receiver),
                        signature=str(signature),
                        source=str(source_token_account),
                        destination=str(destination_token_account),
                        status="confirmed",
                        latest_blockhash=str(recent_blockhash.value.blockhash),
                        amount=data.amount,
                        fee_sol=fee_sol,
                        fee_lamports=fee_lamports,
                        direction="out",
                    )
                else:
                    error_msg = (
                        confirmation.value[0].err
                        if confirmation.value
                        else "Unknown error"
                    )
                    return TransactionSchema(
                        sender=str(owner.pubkey()),
                        recipient=str(receiver),
                        signature=str(signature),
                        status="failed",
                        error=str(error_msg),
                    )
        except Exception as e:
            sender_pubkey_str = self._get_sender_pubkey_str(data.owner_bs58_private_key)
            return TransactionSchema(
                sender=sender_pubkey_str,
                recipient=data.recipient,
                signature=str(signature) if signature else None,
                status="failed",
                error=str(e),
            )

    async def _get_all_mint_details(
        self, client: AsyncClient, mint_addresses: List[str]
    ):
        mint_pubkeys = [Pubkey.from_string(ma) for ma in mint_addresses]
        metadata_pubkeys = [self.get_nft_metadata_account(ma) for ma in mint_addresses]

        all_pubkeys = mint_pubkeys + metadata_pubkeys
        all_accounts = await client.get_multiple_accounts(all_pubkeys)

        mint_account_infos = all_accounts.value[: len(mint_pubkeys)]
        metadata_account_infos = all_accounts.value[len(mint_pubkeys) :]

        mint_details_map = {}
        for i, mint_address in enumerate(mint_addresses):
            mint_account_info = mint_account_infos[i]
            metadata_account_info = metadata_account_infos[i]

            if mint_account_info and metadata_account_info:
                try:
                    mint_data = MINT_LAYOUT.parse(mint_account_info.data)
                    mint_info = MintInfo(
                        mint_authority=mint_data.mint_authority,
                        supply=mint_data.supply,
                        decimals=mint_data.decimals,
                        is_initialized=mint_data.is_initialized,
                        freeze_authority=mint_data.freeze_authority,
                    )

                    token_meta_data = self.unpack_metadata_account(
                        metadata_account_info.data
                    )

                    meta_data_from_uri = await self.fetch_token_metadata_from_uri(
                        token_meta_data.uri
                    )
                    logo = meta_data_from_uri.get("image")

                    if token_meta_data:
                        mint_details_map[mint_address] = (
                            mint_info,
                            token_meta_data,
                            logo,
                        )
                except Exception as e:
                    print(f"Error processing mint details for {mint_address}: {e}")

        return mint_details_map

    async def retrieve_token_accounts(
        self, owner_address: str
    ) -> List[TokenAccountSchema]:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(f"retrieve_token_accounts(owner_address: {owner_address})")
            try:
                owner = Pubkey.from_string(owner_address)
                response = await client.get_token_accounts_by_owner(
                    owner, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
                )

                result = []
                if not response.value:
                    return result

                mint_addresses = set()
                parsed_accounts_data = []
                for account_info in response.value:
                    account_data = ACCOUNT_LAYOUT.parse(account_info.account.data)
                    mint_address = str(Pubkey.from_bytes(account_data.mint))
                    mint_addresses.add(mint_address)
                    parsed_accounts_data.append(
                        {
                            "account_info": account_info,
                            "account_data": account_data,
                            "mint_address": mint_address,
                        }
                    )

                mint_details_map = await self._get_all_mint_details(
                    client, list(mint_addresses)
                )

                for account_data_item in parsed_accounts_data:
                    account_info = account_data_item["account_info"]
                    account_data = account_data_item["account_data"]
                    mint_address = account_data_item["mint_address"]

                    if mint_address in mint_details_map:
                        mint_info, token_meta_data, logo = mint_details_map[
                            mint_address
                        ]

                        mint_token_schema = MintTokenSchema(
                            address=mint_address,
                            decimals=mint_info.decimals,
                            supply=mint_info.supply,
                            is_initialized=mint_info.is_initialized,
                            mint_authority=str(
                                Pubkey.from_bytes(mint_info.mint_authority)
                            ),
                            update_authority=token_meta_data.update_authority,
                            name=token_meta_data.name,
                            symbol=token_meta_data.symbol,
                            uri=token_meta_data.uri,
                            logo=logo,
                            is_mutable=token_meta_data.is_mutable,
                        )

                        token_amount = int(account_data.amount) / (
                            10**mint_token_schema.decimals
                        )

                        result.append(
                            TokenAccountSchema(
                                address=str(account_info.pubkey),
                                owner=str(Pubkey.from_bytes(account_data.owner)),
                                amount=token_amount,
                                account_owner=str(account_info.account.owner),
                                mint_token=mint_token_schema,
                            )
                        )
                return result

            except Exception as e:
                print(f"Error getting token accounts: {e}")
                return []

    def get_nft_metadata_account(self, mint_address: str) -> Pubkey:
        mint_pubkey = Pubkey.from_string(mint_address)
        seeds = [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint_pubkey)]
        # pda, _bump_seed
        pda, _ = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)
        return pda

    def unpack_metadata_account(self, data: bytes) -> TokenMetaDataSchema | None:
        if not data or data[0] != 4:
            return None

        try:
            i = 1
            update_authority = base58.b58encode(data[i : i + 32]).decode("utf-8")
            i += 32
            mint = base58.b58encode(data[i : i + 32]).decode("utf-8")
            i += 32

            def parse_string(buffer, offset):
                length = struct.unpack_from("<I", buffer, offset)[0]
                offset += 4
                return (
                    buffer[offset : offset + length].decode("utf-8").strip("\x00"),
                    offset + length,
                )

            name, i = parse_string(data, i)
            symbol, i = parse_string(data, i)
            uri, i = parse_string(data, i)

            # fee
            _ = struct.unpack_from("<h", data, i)[0]
            i += 2

            creators, verified, share = [], [], []
            if data[i]:
                i += 1
                creator_len = struct.unpack_from("<I", data, i)[0]
                i += 4
                for _ in range(creator_len):
                    creator = base58.b58encode(data[i : i + 32]).decode("utf-8")
                    creators.append(creator)
                    i += 32
                    verified.append(data[i])
                    i += 1
                    share.append(data[i])
                    i += 1

            # primary_sale_happened
            _ = bool(data[i])
            i += 1
            is_mutable = bool(data[i])

            return TokenMetaDataSchema(
                mint=mint,
                name=name,
                symbol=symbol,
                uri=uri,
                is_mutable=is_mutable,
                update_authority=update_authority,
            )
        except Exception as e:
            print(f"Error unpacking metadata: {e}")
            return None

    async def get_token_metadata(
        self, client: AsyncClient, mint: str, retries: int = 3
    ) -> TokenMetaDataSchema | None:
        nft_pda = self.get_nft_metadata_account(mint)
        try:
            acc_info = await client.get_account_info(nft_pda)
            if acc_info and acc_info.value:
                return self.unpack_metadata_account(acc_info.value.data)
        except Exception as e:
            return None

    async def create_token_account(
        self, data: TokenAccountCreationSchema
    ) -> TokenAccountSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(f"create_token_account(self, data: {data})")

            try:
                owner_address = (data.owner or "").strip()
                if owner_address:
                    owner = Pubkey.from_string(data.owner)

                if owner:
                    print("owner", owner)

                payer = self.create_keypair_from_base58_private_key(
                    data.payer_bs58_private_key
                )

                mint_address = Pubkey.from_string(data.mint_token)

                # Get mint token info first, as it's needed in both cases (exists or not)
                mint_token = await self.get_mint_token(data.mint_token)
                if mint_token.error:
                    return TokenAccountSchema(
                        error=f"Failed to get mint token info: {mint_token.error}"
                    )

                associated_token_account = get_associated_token_address(
                    owner, mint_address
                )

                existing_account = await client.get_account_info(
                    associated_token_account
                )
                if existing_account.value:
                    print("Token Account already exist.")
                    account_data = ACCOUNT_LAYOUT.parse(existing_account.value.data)
                    return TokenAccountSchema(
                        address=str(associated_token_account),
                        owner=str(owner),
                        amount=account_data.amount,
                        account_owner=str(existing_account.value.owner),
                        mint=data.mint_token,
                        mint_token=mint_token,
                    )

                # If account does not exist, create it.
                recent_blockhash_resp = await client.get_latest_blockhash()
                recent_blockhash = recent_blockhash_resp.value.blockhash

                create_token_account_instruction = create_associated_token_account(
                    payer=payer.pubkey(),
                    owner=owner,
                    mint=mint_address,
                )

                message = Message.new_with_blockhash(
                    instructions=[create_token_account_instruction],
                    payer=payer.pubkey(),
                    blockhash=recent_blockhash,
                )

                # The payer is the owner, so only one signer.
                transaction = Transaction([payer], message, recent_blockhash)

                fee_response = await client.get_fee_for_message(message)
                fee_lamports = fee_response.value
                fee_sol = self.lamports_to_sol(fee_lamports)

                send_response = await client.send_transaction(transaction)
                signature = send_response.value
                print(f"Transaction sent! Signature: {signature}")

                confirmation = await client.confirm_transaction(
                    signature, commitment=Confirmed, sleep_seconds=1
                )

                if confirmation.value and confirmation.value[0].err is None:
                    print("Token account created successfully!")
                    return TokenAccountSchema(
                        address=str(associated_token_account),
                        owner=str(owner),
                        mint=data.mint_token,
                        mint_token=mint_token,
                        fee_lamports=fee_lamports,
                        fee_sol=fee_sol,
                    )
                else:
                    error_msg = (
                        confirmation.value[0].err
                        if confirmation.value
                        else "Unknown error"
                    )
                    print(f"Transaction failed: {error_msg}")
                    return TokenAccountSchema(error=str(error_msg))

            except Exception as e:
                print(f"Error creating token account: {e}")
                traceback.print_exc()
                return TokenAccountSchema(error=str(e))

    async def fetch_token_metadata_from_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        try:
            normalized_uri = self.normalize_metadata_uri(uri)
            print(f"Fetching metadata from: {normalized_uri}")

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; MetadataFetcher/1.0)",
                "Accept": "application/json, text/plain, */*",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    normalized_uri, timeout=30, headers=headers
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        content = content.strip()
                        try:
                            metadata = json.loads(content)
                            return metadata
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            print(f"Raw content: {content[:200]}...")
                            return None
                    else:
                        print(f"HTTP {response.status} from {uri}")
                        return None

        except Exception as e:
            print(f"Error fetching metadata from {uri}: {e}")
            return None

    def normalize_metadata_uri(self, uri: str) -> str:
        if uri.startswith("ipfs://"):
            # convert ipfs://Qm... → https://ipfs.io/ipfs/Qm...
            ipfs_hash = uri.replace("ipfs://", "")
            return f"https://ipfs.io/ipfs/{ipfs_hash}"

        elif uri.startswith("ar://"):
            # convert ar://... → https://arweave.net/...
            arweave_hash = uri.replace("ar://", "")
            return f"https://arweave.net/{arweave_hash}"

        elif uri.startswith("https://") or uri.startswith("http://"):
            return uri

        else:
            # IPFS hash without prefix
            return f"https://ipfs.io/ipfs/{uri}"

    def parse_token_balances(
        self,
        meta: Dict[str, Any],
        message: Dict[str, Any],
        transaction: TransactionSchema = None,
        is_shrink: bool = False,
    ):
        """Parse token balance changes and account address"""
        pre_token_balances = meta.get("preTokenBalances", [])
        post_token_balances = meta.get("postTokenBalances", [])
        account_keys = message.get("accountKeys", [])

        found_index = -1
        account_index = -1
        result = None

        token_balances = []

        if is_shrink and transaction and transaction.mint_token:
            for i, post_balance in enumerate(post_token_balances):
                owner = post_balance.get("owner")
                if owner == transaction.source or owner == transaction.owner:
                    found_index = i
                    print(
                        f"""Found matching post token balance at index {found_index}"""
                    )

                    account_index = post_balance.get("accountIndex")
                    post_amount = post_balance.get("uiTokenAmount", {})
                    mint = post_balance.get("mint")

                    # Find corresponding pre balance
                    pre_balance = next(
                        (
                            b
                            for b in pre_token_balances
                            if b.get("accountIndex") == account_index
                            and b.get("mint") == mint
                        ),
                        None,
                    )
                    # Calculate changes
                    if pre_balance:
                        pre_amount = pre_balance.get("uiTokenAmount", {})
                        pre_ui_amount = pre_amount.get("uiAmount", 0) or 0
                    else:
                        pre_ui_amount = 0

                    post_ui_amount = post_amount.get("uiAmount", 0) or 0
                    change = post_ui_amount - pre_ui_amount

                    # Get actual account address
                    if account_index < len(account_keys):
                        account_address = account_keys[account_index].get(
                            "pubkey", f"Account_{account_index}"
                        )
                    else:
                        account_address = f"Account_{account_index}"

                    # Only add if there is a change or a balance
                    if change != 0 or post_ui_amount != 0:
                        result = {
                            "address": account_address,
                            "token": mint,
                            "changes": change,
                            "post_balance": f"{post_ui_amount} {transaction.symbol if transaction and transaction.symbol else "SOL" or ''}".strip(),
                        }
                        token_balances.append(result)
            return token_balances

        else:
            # Process each post token balance
            for post_balance in post_token_balances:
                account_index = post_balance.get("accountIndex")
                mint = post_balance.get("mint")
                post_amount = post_balance.get("uiTokenAmount", {})

                # Get actual account address
                if account_index < len(account_keys):
                    account_address = account_keys[account_index].get(
                        "pubkey", f"Account_{account_index}"
                    )
                else:
                    account_address = f"Account_{account_index}"

                # Find corresponding pre balance
                pre_balance = next(
                    (
                        b
                        for b in pre_token_balances
                        if b.get("accountIndex") == account_index
                        and b.get("mint") == mint
                    ),
                    None,
                )

                # Calculate changes
                if pre_balance:
                    pre_amount = pre_balance.get("uiTokenAmount", {})
                    pre_ui_amount = pre_amount.get("uiAmount", 0) or 0
                else:
                    pre_ui_amount = 0

                post_ui_amount = post_amount.get("uiAmount", 0) or 0
                change = post_ui_amount - pre_ui_amount

                # Only add if there is a change or a balance
                if change != 0 or post_ui_amount != 0:
                    token_balances.append(
                        {
                            "address": account_address,
                            "token": mint,
                            "changes": change,
                            "post_balance": f"{post_ui_amount} {transaction.symbol if transaction and transaction.symbol else "SOL" or ''}".strip(),
                        }
                    )
            return token_balances

    def parse_account_inputs(
        self,
        message: Dict[str, Any],
        meta: Dict[str, Any],
        raw_transaction: TransactionSchema,
        is_shrink: bool = False,
    ):
        """Parse account inputs and balance changes"""
        account_keys = message.get("accountKeys", [])
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])

        if is_shrink and raw_transaction.source:
            index = -1
            found_account_key = None
            for i, account in enumerate(account_keys):
                if i >= len(pre_balances) or i >= len(post_balances):
                    continue
                if account.get("pubkey") != raw_transaction.source:
                    found_account_key = account
                    index = i
                    break
            if index == -1:
                return None

            pubkey = found_account_key.get("pubkey", "")
            pre_balance_sol = pre_balances[index] / 1e9
            post_balance_sol = post_balances[index] / 1e9
            change_sol = post_balance_sol - pre_balance_sol

            # Create account details
            details = []
            if found_account_key.get("signer", False):
                details.append("Signer")
            if found_account_key.get("writable", False):
                details.append("Writable")

            # Add fee payer if it's the first account and is a signer
            if index == 0 and found_account_key.get("signer", False):
                details.append("Fee Payer")

            result = {
                "is_payer": i == 0 and account.get("signer", False),
                "address": pubkey,
                "changes": round(change_sol, 9),
                "post_balance": round(post_balance_sol, 9),
                "details": details,
            }
            return result
        else:
            account_inputs = []
            for i, account in enumerate(account_keys):
                if i >= len(pre_balances) or i >= len(post_balances):
                    continue

                pubkey = account.get("pubkey", "")
                pre_balance_sol = pre_balances[i] / 1e9
                post_balance_sol = post_balances[i] / 1e9
                change_sol = post_balance_sol - pre_balance_sol

                # Create account details
                details = []
                if account.get("signer", False):
                    details.append("Signer")
                if account.get("writable", False):
                    details.append("Writable")

                # Add fee payer if it's the first account and is a signer
                if i == 0 and account.get("signer", False):
                    details.append("Fee Payer")

                account_inputs.append(
                    {
                        "is_payer": i == 0 and account.get("signer", False),
                        "address": pubkey,
                        "changes": round(change_sol, 9),
                        "post_balance": round(post_balance_sol, 9),
                        "details": details,
                    }
                )
            return account_inputs

    def parse_transaction_to_desired_format(
        self,
        transaction_data: Dict[str, Any],
        raw_transaction: TransactionSchema,
        is_shrink: bool = False,
    ) -> Dict[str, Any]:
        """
        Parse transaction data from jsonParsed format to desired format
        """
        result = transaction_data.get("result", {})
        meta = result.get("meta", {})
        transaction_info = result.get("transaction", {})
        message = transaction_info.get("message", {})
        signatures = transaction_info.get("signatures", {})

        # 1. ACCOUNT INPUTS SECTION
        account_inputs = self.parse_account_inputs(
            message,
            meta,
            raw_transaction=raw_transaction,
            is_shrink=is_shrink,
        )

        # locate the payer account (where is_payer == True)
        payer_account = None
        if isinstance(account_inputs, list):
            payer_account = next(
                (acc for acc in account_inputs if acc.get("is_payer")), None
            )
            payer_address = (
                payer_account["address"]
                if payer_account
                else (account_inputs[0]["address"] if account_inputs else None)
            )
        else:
            payer_address = (
                account_inputs["address"] if account_inputs.get("is_payer") else None
            )

        # 2. TOKEN BALANCES SECTION
        token_balances = self.parse_token_balances(
            meta, message, raw_transaction, is_shrink=is_shrink
        )

        # 3. OVERVIEW SECTION
        overview = {
            "signature": signatures,
            "result": "Success" if meta.get("err") is None else "Failed",
            "timestamp": result.get("blockTime", 0),
            "confirmation_status": "finalized",
            "confirmations": "max",
            "slot": result.get("slot", 0),
            "recent_blockhash": message.get("recentBlockhash", ""),
            "fee": meta.get("fee", 0) / 1e9,  # convert to SOL
            "compute_units_consumed": meta.get("computeUnitsConsumed", 0),
            "transaction_cost": (meta.get("fee", 0) + 2039280)
            / 1e9,  # Fee + rent exemption
            "reserved_cus": 400000,  # from log messages: "consumed 20641 of 400000 compute units"
            "transaction_version": (
                "legacy"
                if result.get("version") == "legacy"
                else f"{result.get('version', 0)}"
            ),
            "payer_address": payer_address if payer_address else None,
        }

        classifier = SolanaTransactionClassifier()
        transaction_type = classifier.get_transaction_type(transaction_data)

        return {
            "overview": overview,
            "account_inputs": account_inputs,
            "token_balances": token_balances,
            "transaction_type": transaction_type.value,
        }

    async def process_transaction(
        self,
        transaction_data: Dict[str, Any],
        transaction: TransactionSchema = None,
        is_shrink: bool = False,
    ) -> Dict[str, Any]:
        try:
            parsed_data = self.parse_transaction_to_desired_format(
                transaction_data, transaction, is_shrink
            )
            return parsed_data

        except Exception as e:
            return {"error": f"Parse error: {str(e)}", "raw_data": transaction_data}

    async def fetch_transactions_by_owner(self, data: TransactionRetrieverSchema):
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            before_signature = (data.before_signature or "").strip()
            until_signature = (data.until_signature or "").strip()
            account_signatures = await client.get_signatures_for_address(
                account=Pubkey.from_string(data.account),
                before=(
                    Signature.from_string(before_signature)
                    if before_signature
                    else None
                ),
                until=(
                    Signature.from_string(until_signature) if until_signature else None
                ),
                limit=data.limit,
                commitment=Finalized,
            )

            child_token_accounts = await self.retrieve_token_accounts(data.account)
            # print("child_token_accounts", child_token_accounts)

            # transactions = []
            parsed_transactions = []
            parent_signatures = set()
            child_signatures = set()

            # add all primary signatures to parent_signatures to avoid processing duplicates later
            for i, raw_transaction in enumerate[Any](account_signatures.value):
                parent_signatures.add(
                    TransactionSchema(
                        signature=str(raw_transaction.signature),
                        owner=data.account,
                        source=data.account,
                        token="Solana",
                        symbol="SOL",
                        mint_token=WRAPPED_SOL_MINT,
                    )
                )

            for j, token_account in enumerate(child_token_accounts):
                print(f"token_account-{j}", token_account.address, "\n")
                child_token_account_signatures = (
                    await client.get_signatures_for_address(
                        account=Pubkey.from_string(token_account.address),
                        before=(
                            Signature.from_string(before_signature)
                            if before_signature
                            else None
                        ),
                        until=(
                            Signature.from_string(until_signature)
                            if until_signature
                            else None
                        ),
                        limit=data.limit,
                        commitment=Finalized,
                    )
                )

                for k, child_signature in enumerate(
                    child_token_account_signatures.value
                ):
                    child_signatures.add(
                        TransactionSchema(
                            signature=str(child_signature.signature),
                            owner=data.account,
                            source=token_account.address,
                            token=token_account.mint_token.name,
                            symbol=token_account.mint_token.symbol,
                            mint_token=token_account.mint_token,
                        )
                    )

            all_raw_transactions = parent_signatures.union(child_signatures)
            print("all_signatures to process:", len(all_raw_transactions), "\n")

            for raw_transaction in all_raw_transactions:
                transaction = await client.get_transaction(
                    Signature.from_string(raw_transaction.signature),
                    "jsonParsed",
                    max_supported_transaction_version=0,
                )
                parsed_transaction = await self.process_transaction(
                    json.loads(transaction.to_json()),
                    transaction=raw_transaction,
                    is_shrink=True,
                )
                # print("parsed_transaction", json.dumps(parsed_transaction), "\n")
                parsed_transactions.insert(
                    0,
                    {
                        "signature": f"{raw_transaction.signature}",
                        **parsed_transaction,
                    },
                )
            return parsed_transactions

    async def fetch_transactions(self, signature: str, parsed_json: bool = False):
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(
                f"fetch_transactions(signature={signature}, parsed_json={parsed_json})"
            )
            transaction = await client.get_transaction(
                Signature.from_string(signature),
                "jsonParsed",
                max_supported_transaction_version=0,
            )
            return (
                await self.process_transaction(json.loads(transaction.to_json()))
                if parsed_json
                else json.loads(transaction.to_json())
            )
