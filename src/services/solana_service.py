from typing import List
import json
import time

import base58
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solana.constants import LAMPORTS_PER_SOL
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token._layouts import MINT_LAYOUT, ACCOUNT_LAYOUT
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.core import MintInfo
from solders.system_program import transfer, TransferParams
from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from schemas.token_schemas import (
    MintTokenSchema,
    TransferTokenCreationSchema,
    TokenMetaDataSchema,
    TokenAccountSchema,
)
from schemas.wallet_schemas import WalletModelCreationSchema, WalletModelSchema
from schemas.transaction_schemas import TransactionSchema

import requests
from requests.structures import CaseInsensitiveDict
import struct

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
                freeze_authority_keypair = Pubkey.from_bytes(mint_info.freeze_authority)

                # fetch token meta data
                token_meta_data = await self.get_token_metadata(mint_address)

                return MintTokenSchema(
                    address=mint_address,
                    owner=str(account_info.value.owner),
                    lamports=account_info.value.lamports,
                    decimals=mint_info.decimals,
                    supply=mint_info.supply,
                    is_initialized=mint_info.is_initialized,
                    mint_authority=str(authority_keypair),
                    freeze_authority=str(freeze_authority_keypair),
                    update_authority=token_meta_data.update_authority,
                    name=token_meta_data.name,
                    symbol=token_meta_data.symbol,
                    uri=token_meta_data.uri,
                    seller_fee_basis_points=token_meta_data.seller_fee_basis_points,
                    creators=token_meta_data.creators,
                    verified=token_meta_data.verified,
                    share=token_meta_data.share,
                    primary_sale_happened=token_meta_data.primary_sale_happened,
                    is_mutable=token_meta_data.is_mutable,
                )
            except Exception as e:
                print(f"❌ Get mint token info from Solana is error: {e}")
                return MintTokenSchema(error=f"❌ Solana return: {e}")

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

    async def prepare_to_transfer_sol(
        self,
        sender_base58_private_key: str,
        recipient_address: str,
        amount: float,
    ) -> TransactionSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            try:
                sender, _, message = await self._prepare_sol_transfer_information(
                    sender_base58_private_key, recipient_address, amount, client
                )
                fee_response = await client.get_fee_for_message(message)
                fee_lamports = fee_response.value
                fee_sol = self.lamports_to_sol(fee_lamports)

                return TransactionSchema(
                    sender=str(sender.pubkey()),
                    recipient=recipient_address,
                    amount=amount,
                    fee_lamports=fee_lamports,
                    fee_sol=fee_sol,
                    status="prepared",
                )
            except Exception as e:
                return TransactionSchema(
                    sender=str(sender.pubkey()),
                    recipient=recipient_address,
                    amount=amount,
                    status=str(e),
                )

    async def send_sol(
        self,
        sender_base58_private_key: str,
        recipient_address: str,
        amount: float,
    ) -> TransactionSchema:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            try:
                sender, transfer_amount, message = (
                    await self._prepare_sol_transfer_information(
                        sender_base58_private_key, recipient_address, amount, client
                    )
                )

                fee_response = await client.get_fee_for_message(message)
                fee_lamports = fee_response.value
                fee_sol = self.lamports_to_sol(fee_lamports)

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
                    print("✅ Transaction successful!")
                    return TransactionSchema(
                        sender=str(sender.pubkey()),
                        recipient=recipient_address,
                        signature=str(signature),
                        status="confirmed",
                        amount=amount,
                        total_sol=amount + fee_sol,
                        total_lamports=transfer_amount + fee_lamports,
                        fee_sol=fee_sol,
                        fee_lamports=fee_lamports,
                        token="Solana",
                        symbol="SOL",
                        direction="out",
                        timestamp=int(time.time()),
                    )
                else:
                    print(f"❌ Transaction failed: {confirmation.value[0].err}")
                    return TransactionSchema(
                        sender=str(sender.pubkey()),
                        recipient=recipient_address,
                        signature=str(signature),
                        status="failed",
                        amount=amount,
                        token="Solana",
                        symbol="SOL",
                        direction="out",
                        timestamp=int(time.time()),
                        error=str(confirmation.value[0].err),
                    )

            except Exception as e:
                return TransactionSchema(
                    sender=str(sender.pubkey()),
                    recipient=recipient_address,
                    signature=str(signature),
                    status="failed",
                    amount=amount,
                    token="Solana",
                    symbol="SOL",
                    direction="out",
                    timestamp=int(time.time()),
                    error=str(e),
                )

    async def send_tokens(self):
        print("send_tokens")

    async def retrieve_token_accounts(
        self, owner_address: str
    ) -> List[TokenAccountSchema]:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(f"retrieve_token_accounts(owner_address: {owner_address})")
            try:
                owner = Pubkey.from_string(owner_address)
                # Get all token accounts by owner
                response = await client.get_token_accounts_by_owner(
                    owner, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
                )

                result = []
                for account_info in response.value:
                    # Parse mint data using layout
                    account_data = ACCOUNT_LAYOUT.parse(account_info.account.data)
                    mint_data = MINT_LAYOUT.parse(account_info.account.data)
                    token_meta_data = await self.get_mint_token(
                        mint_address=str(Pubkey.from_bytes(account_data.mint))
                    )
                    result.append(
                        TokenAccountSchema(
                            address=str(account_info.pubkey),
                            account_owner=str(account_info.account.owner),
                            lamports=account_info.account.lamports,
                            data_length=len(account_info.account.data),
                            decimals=mint_data.decimals,
                            supply=mint_data.supply,
                            is_initialized=mint_data.is_initialized,
                            mint_authority=str(
                                Pubkey.from_bytes(mint_data.mint_authority)
                            ),
                            freeze_authority=str(
                                Pubkey.from_bytes(mint_data.freeze_authority)
                            ),
                            mint=str(Pubkey.from_bytes(account_data.mint)),
                            owner=str(Pubkey.from_bytes(account_data.owner)),
                            amount=account_data.amount,
                            delegate_option=account_data.delegate_option,
                            delegate=str(Pubkey.from_bytes(account_data.delegate)),
                            state=account_data.state,
                            is_native_option=account_data.is_native_option,
                            is_native=account_data.is_native,
                            delegated_amount=account_data.delegated_amount,
                            close_authority_option=account_data.close_authority_option,
                            close_authority=str(
                                Pubkey.from_bytes(account_data.close_authority)
                            ),
                            token_meta_data=token_meta_data,
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

            fee = struct.unpack_from("<h", data, i)[0]
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

            primary_sale_happened = bool(data[i])
            i += 1
            is_mutable = bool(data[i])

            return TokenMetaDataSchema(
                update_authority=update_authority,
                mint=mint,
                name=name,
                symbol=symbol,
                uri=uri,
                seller_fee_basis_points=fee,
                creators=creators,
                verified=verified,
                share=share,
                primary_sale_happened=primary_sale_happened,
                is_mutable=is_mutable,
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
