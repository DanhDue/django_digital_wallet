import asyncio
import json
import struct
import time
import traceback
from typing import List

import base58
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator
from solana.constants import LAMPORTS_PER_SOL
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.message import Message, MessageV0
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction, VersionedTransaction
from spl.token._layouts import ACCOUNT_LAYOUT, MINT_LAYOUT
from spl.token.constants import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID
from spl.token.core import MintInfo
from spl.token.instructions import (
    TransferCheckedParams,
    create_associated_token_account,
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
from schemas.transaction_schemas import TransactionSchema
from schemas.wallet_schemas import WalletModelCreationSchema, WalletModelSchema

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

    async def airdrop(self, address: str, amount: float = 5.0) -> dict:
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
                return WalletModelSchema(
                    error=f"{e if (str(e) or "").strip() else 'Cannot airdrop now. Please try again.'}"
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
        secret_bytes = bytes(keypair)
        return WalletModelSchema(
            bs58PrivateKey=base58.b58encode(secret_bytes).decode(),
            privateKey=str(list[int](secret_bytes)),
            address=str(keypair.pubkey()),
            mnemonics=mnemonics,
            balance=0,
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
            return self._create_wallet_model_from_keypair(keypair)
        except ValueError as e:
            print(f"Failed to parse secret key: {e}")
            return WalletModelSchema()

    def _restore_wallet_from_bs58_key(self, bs58_private_key: str) -> WalletModelSchema:
        try:
            keypair = Keypair.from_base58_string(bs58_private_key)
            return self._create_wallet_model_from_keypair(keypair)
        except Exception as e:
            print(f"Failed to parse bs58 private key: {e}")
            return WalletModelSchema()

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
                token_meta_data = await self.get_token_metadata(mint_address)

                print("token_meta_data", token_meta_data)

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
                    commitment="confirmed",
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
                    token_account_creation_instruction = create_associated_token_account(
                        payer=payer.pubkey(),
                        owner=receiver,
                        mint=mint_address,
                    )
                    token_account_creation_msg = Message.new_with_blockhash(
                        instructions=[token_account_creation_instruction],
                        payer=payer.pubkey(),
                        blockhash=recent_blockhash.value.blockhash,
                    )
                    fee_response = await client.get_fee_for_message(token_account_creation_msg)
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

                    token_account_creation_instruction = create_associated_token_account(
                        payer=payer.pubkey(),
                        owner=receiver,
                        mint=mint_address,
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
                    signature, commitment="confirmed", sleep_seconds=1
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

    async def _get_mint_details(self, client: AsyncClient, mint_address: str):
        mint_address_key = Pubkey.from_string(mint_address)
        
        try:
            mint_account_info_task = client.get_account_info(mint_address_key)
            token_meta_data_task = self.get_token_metadata(mint_address)
            
            mint_account_info_resp, token_meta_data = await asyncio.gather(
                mint_account_info_task, token_meta_data_task, return_exceptions=True
            )

            if isinstance(mint_account_info_resp, Exception):
                print(f"Error fetching mint account info for {mint_address}: {mint_account_info_resp}")
                return None, None
            if isinstance(token_meta_data, Exception):
                print(f"Error fetching token metadata for {mint_address}: {token_meta_data}")
                return None, None
            
            mint_data = MINT_LAYOUT.parse(mint_account_info_resp.value.data)
            mint_info = MintInfo(
                mint_authority=mint_data.mint_authority,
                supply=mint_data.supply,
                decimals=mint_data.decimals,
                is_initialized=mint_data.is_initialized,
                freeze_authority=mint_data.freeze_authority,
            )
            
            return mint_info, token_meta_data
        except Exception as e:
            print(f"Unexpected error in _get_mint_details for {mint_address}: {e}")
            return None, None

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
                    parsed_accounts_data.append({
                        "account_info": account_info,
                        "account_data": account_data,
                        "mint_address": mint_address
                    })

                # Fetch all unique mint details concurrently
                mint_details_tasks = [self._get_mint_details(client, ma) for ma in mint_addresses]
                all_mint_details = await asyncio.gather(*mint_details_tasks)
                
                mint_details_map = {}
                for i, mint_address in enumerate(list(mint_addresses)): # Convert set to list to maintain order
                    mint_details_map[mint_address] = all_mint_details[i]

                for account_data_item in parsed_accounts_data:
                    account_info = account_data_item["account_info"]
                    account_data = account_data_item["account_data"]
                    mint_address = account_data_item["mint_address"]

                    mint_info, token_meta_data = mint_details_map.get(mint_address, (None, None))

                    if mint_info and token_meta_data:
                        mint_token_schema = MintTokenSchema(
                            address=mint_address,
                            decimals=mint_info.decimals,
                            supply=mint_info.supply,
                            is_initialized=mint_info.is_initialized,
                            mint_authority=str(Pubkey.from_bytes(mint_info.mint_authority)),
                            update_authority=token_meta_data.update_authority,
                            name=token_meta_data.name,
                            symbol=token_meta_data.symbol,
                            uri=token_meta_data.uri,
                            is_mutable=token_meta_data.is_mutable,
                        )
                        result.append(
                            TokenAccountSchema(
                                address=str(account_info.pubkey),
                                owner=str(Pubkey.from_bytes(account_data.owner)),
                                amount=account_data.amount,
                                account_owner=str(account_info.account.owner),
                                mint_token=mint_token_schema,
                            )
                        )
                return result

            except Exception as e:
                print(f"Error getting token accounts: {e}")
                return []

    def get_nft_metadata_account(self, mint_address: str) -> Pubkey:
        """
        Derives the Program Derived Address (PDA) for a given NFT mint key on Solana.
        This PDA is used to locate the metadata account for an NFT on the Solana blockchain.

        Args:
            mint_address (str): The public key of the NFT's mint account, as a string.

        Returns:
            Pubkey: The derived Program Derived Address (PDA) associated with the NFT metadata.
        """
        mint_pubkey = Pubkey.from_string(mint_address)
        seeds = [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint_pubkey)]
        pda, _bump_seed = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)
        return pda

    def unpack_metadata_account(self, data: bytes) -> dict | None:
        """
        Unpacks and parses the raw byte data of an NFT metadata account on the Solana blockchain.

        Args:
            data (bytes): Raw byte data containing NFT metadata.

        Returns:
            dict: A dictionary containing the unpacked metadata, or None if parsing fails.
        """
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
        self, mint: str, retries: int = 3
    ) -> TokenMetaDataSchema | None:
        """
        Fetches and returns the metadata for a given NFT mint key on the Solana blockchain.
        Includes a retry mechanism for fetching the account information.

        Args:
            mint (str): The public key of the NFT's mint account.
            retries (int): The number of times to retry fetching the account info.

        Returns:
            dict: A dictionary containing the NFT metadata, or None if it fails.
        """
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            nft_pda = self.get_nft_metadata_account(mint)
            for attempt in range(retries):
                try:
                    acc_info = await client.get_account_info(nft_pda)
                    if acc_info and acc_info.value:
                        return self.unpack_metadata_account(acc_info.value.data)
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt + 1 == retries:
                        return None
        return None

    async def create_token_account(
        self, data: TokenAccountCreationSchema
    ) -> TokenAccountSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(f"create_token_account(self, data: {data})")

            try:
                owner = self.create_keypair_from_base58_private_key(
                    data.owner_bs58_private_key
                )

                payer = self.create_keypair_from_base58_private_key(
                    data.owner_bs58_private_key
                )

                mint_address = Pubkey.from_string(data.mint_token)

                # Get associated token account address
                associated_token_account = get_associated_token_address(
                    owner.pubkey(), mint_address
                )

                existing_account = await client.get_account_info(
                    associated_token_account
                )
                if existing_account.value:
                    print("Token Account already exist.")
                    account_data = ACCOUNT_LAYOUT.parse(existing_account.value.data)

                    mint_token = await self.get_mint_token(data.mint_token)

                    return TokenAccountSchema(
                        address=str(associated_token_account),
                        owner=str(owner.pubkey()),
                        amount=account_data.amount,
                        account_owner=str(existing_account.value.owner),
                        mint=data.mint_token,
                        mint_token=mint_token,
                    )

                # Get latest blockhash
                recent_blockhash_resp = await client.get_latest_blockhash()
                recent_blockhash = recent_blockhash_resp.value.blockhash

                # Create associated token account instruction
                create_token_account_instruction = create_associated_token_account(
                    payer=(payer.pubkey() if payer else owner.pubkey()),
                    owner=owner.pubkey(),
                    mint=mint_address,
                )

                # Create message
                message = Message.new_with_blockhash(
                    instructions=[create_token_account_instruction],
                    payer=(payer.pubkey() if payer else owner.pubkey()),
                    blockhash=recent_blockhash,
                )

                # Create transaction
                transaction = Transaction(
                    ([owner] if not payer else [owner, payer]),
                    message,
                    recent_blockhash,
                )

                fee_response = await client.get_fee_for_message(message)
                fee_lamports = fee_response.value
                fee_sol = self.lamports_to_sol(fee_lamports)

                send_response = await client.send_transaction(transaction)
                signature = send_response.value
                print(f"Transaction sent! Signature: {signature}")

                confirmation = await client.confirm_transaction(
                    signature, commitment="confirmed", sleep_seconds=1
                )

                if confirmation.value and confirmation.value[0].err is None:
                    print("Token account created successfully!")
                    mint_token = await self.get_mint_token(data.mint_token)
                    return TokenAccountSchema(
                        address=str(associated_token_account),
                        owner=str(owner.pubkey()),
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
