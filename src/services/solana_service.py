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
from spl.token._layouts import MINT_LAYOUT
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.core import MintInfo
from solders.system_program import transfer, TransferParams
from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from schemas.token_schemas import MintTokenSchema, TransferTokenCreationSchema
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
                print("get_mint_token:", mint_address_key)

                # meta_data = await self.get_metadata(
                #     mint="DttvtPZ92yZrzUTeF8jqtDXaQLDGVHVx5acNhEtLVH2w"
                # )
                # print("meta_data", meta_data)

                meta_data = await self.get_token_metadata_manual(
                    mint_address="DttvtPZ92yZrzUTeF8jqtDXaQLDGVHVx5acNhEtLVH2w"
                )
                print("meta_data", meta_data)

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

                return MintTokenSchema(
                    address=mint_address,
                    owner=str(account_info.value.owner),
                    lamports=account_info.value.lamports,
                    decimals=mint_info.decimals,
                    supply=mint_info.supply,
                    is_initialized=mint_info.is_initialized,
                    mint_authority=str(authority_keypair),
                    freeze_authority=str(freeze_authority_keypair),
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
    ) -> List[MintTokenSchema]:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            print(f"retrieve_token_accounts(owner_address: {owner_address})")
            try:
                owner = Pubkey.from_string(owner_address)
                # Get all token accounts by owner
                response = await client.get_token_accounts_by_owner(
                    owner, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
                )

                print(f"Owner: {owner}")
                print(f"Found {len(response.value)} token accounts:\n")

                result = []
                for account_info in response.value:
                    print("account_info", account_info)
                    print(f"Pubkey: {account_info.pubkey}")
                    print(f"Owner: {account_info.account.owner}")
                    print(f"Lamports: {account_info.account.lamports}")
                    print(f"Data Length: {len(account_info.account.data)} bytes")

                    # Parse mint data using layout
                    mint_data = MINT_LAYOUT.parse(account_info.account.data)
                    print("mint_data", mint_data)

                    result.append(
                        MintTokenSchema(
                            address=str(account_info.pubkey),
                            owner=str(account_info.account.owner),
                            lamports=account_info.account.lamports,
                            decimals=mint_data.decimals,
                            supply=mint_data.supply,
                            is_initialized=mint_data.is_initialized,
                            mint_authority=str(
                                Pubkey.from_bytes(mint_data.mint_authority)
                            ),
                            freeze_authority=str(
                                Pubkey.from_bytes(mint_data.freeze_authority)
                            ),
                        )
                    )
                return result

            except Exception as e:
                print(f"Error getting token accounts: {e}")
                return []

    def get_nft_metadata_account(self, mint: str) -> Pubkey:
        """
        Derives the Program Derived Address (PDA) for a given NFT mint key on Solana.
        This PDA is used to locate the metadata account for an NFT on the Solana blockchain.

        Args:
            mint_key (str): The public key of the NFT's mint account, as a string.

        Returns:
            Pubkey: The derived Program Derived Address (PDA) associated with the NFT metadata.
        """

        # Convert the mint_key (string) into a Pubkey object
        mint_pubkey = Pubkey.from_string(mint)

        # Define the seeds for deriving the PDA
        # The seed includes: a string literal 'metadata', the metadata program ID, and the mint public key
        seeds = [
            b"metadata",  # Constant string seed
            bytes(
                METADATA_PROGRAM_ID
            ),  # Byte representation of the metadata program's public key
            bytes(mint_pubkey),  # Byte representation of the NFT mint's public key
        ]

        # Pubkey.find_program_address() returns a tuple (PDA, bump seed)
        pda, _bump_seed = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)
        print("pda", pda)
        return pda

    def unpack_metadata_account(self, data: bytes) -> dict:
        """
        Unpacks and parses the raw byte data of an NFT metadata account on the Solana blockchain.

        Args:
            data (bytes): Raw byte data containing NFT metadata.

        Returns:
            dict: A dictionary containing the unpacked metadata, including update authority, mint,
                name, symbol, URI, seller fee, creator information, and more.
        """

        # Ensure the first byte indicates a valid metadata account (4)
        assert data[0] == 4

        # Initialize byte index
        i = 1

        # Unpack the update authority (32 bytes)
        source_account = base58.b58encode(
            bytes(struct.unpack("<" + "B" * 32, data[i : i + 32]))
        )
        i += 32

        # Unpack the mint account (32 bytes)
        mint_account = base58.b58encode(
            bytes(struct.unpack("<" + "B" * 32, data[i : i + 32]))
        )
        i += 32

        # Unpack the length and name of the NFT (variable length)
        name_len = struct.unpack("<I", data[i : i + 4])[0]
        i += 4
        name = struct.unpack("<" + "B" * name_len, data[i : i + name_len])
        i += name_len

        # Unpack the length and symbol of the NFT (variable length)
        symbol_len = struct.unpack("<I", data[i : i + 4])[0]
        i += 4
        symbol = struct.unpack("<" + "B" * symbol_len, data[i : i + symbol_len])
        i += symbol_len

        # Unpack the length and URI of the NFT (variable length)
        uri_len = struct.unpack("<I", data[i : i + 4])[0]
        i += 4
        uri = struct.unpack("<" + "B" * uri_len, data[i : i + uri_len])
        i += uri_len

        # Unpack the seller fee (2 bytes)
        fee = struct.unpack("<h", data[i : i + 2])[0]
        i += 2

        # Check if creators are present (1 byte)
        has_creator = data[i]
        i += 1

        # Initialize creator-related lists
        creators = []
        verified = []
        share = []

        # If there are creators, unpack their data
        if has_creator:
            creator_len = struct.unpack("<I", data[i : i + 4])[0]
            i += 4
            for _ in range(creator_len):
                creator = base58.b58encode(
                    bytes(struct.unpack("<" + "B" * 32, data[i : i + 32]))
                )
                creators.append(creator)
                i += 32

                # Unpack the verified status (1 byte per creator)
                verified.append(data[i])
                i += 1

                # Unpack the creator's share (1 byte per creator)
                share.append(data[i])
                i += 1

        # Unpack the primary sale happened flag (1 byte)
        primary_sale_happened = bool(data[i])
        i += 1

        # Unpack the mutability flag (1 byte)
        is_mutable = bool(data[i])

        # Structure the unpacked metadata into a dictionary
        metadata = {
            "update_authority": source_account,
            "mint": mint_account,
            "data": {
                "name": bytes(name)
                .decode("utf-8")
                .strip("\x00"),  # Remove null characters
                "symbol": bytes(symbol)
                .decode("utf-8")
                .strip("\x00"),  # Remove null characters
                "uri": bytes(uri)
                .decode("utf-8")
                .strip("\x00"),  # Remove null characters
                "seller_fee_basis_points": fee,  # Seller's fee in basis points (1/100 of a percent)
                "creators": creators,
                "verified": verified,
                "share": share,
            },
            "primary_sale_happened": primary_sale_happened,
            "is_mutable": is_mutable,
        }

        return metadata

    async def get_metadata(self, mint: str) -> dict:
        async with AsyncClient(self.endpoint, timeout=30.0) as client:

            """
            Fetches and returns the metadata for a given NFT mint key on the Solana blockchain.

            Args:
                mint_key (str): The public key of the NFT's mint account.

            Returns:
                dict: A dictionary containing the NFT metadata such as name, symbol, URI, and creator information.
            """

            # Derive the Program Derived Address (PDA) for the NFT metadata
            nft_pda = self.get_nft_metadata_account(mint)

            # In case of an error try to fetch data 2 more times
            try:

                # Fetch account information for the derived PDA
                acc_info = await client.get_account_info(nft_pda)

                print("acc_info", acc_info)

                # Check if the account data is available
                if not acc_info or not acc_info.value:
                    raise ValueError(f"No account information found for PDA: {nft_pda}")

            except Exception as e:
                print(e)

            # Extract raw data from the account
            data = acc_info.value.data

            danhdue_exoictif = base58.b58encode(bytes(data))

            print("danhdue_exoictif", danhdue_exoictif)

            # Unpack the metadata from the raw data
            token_metadata = self.unpack_metadata_account(data)

            # Return the decoded metadata
            return token_metadata

    async def get_token_metadata_manual(self, mint_address: str):
        async with AsyncClient(self.endpoint, timeout=30.0) as client:
            try:
                mint_pubkey = Pubkey.from_string(mint_address)

                # Find metadata account PDA
                seeds = [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint_pubkey)]
                pda = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)[0]

                print("pda", pda)

                # Get account info
                account_info = await client.get_account_info(pda)

                if account_info.value and account_info.value.data:
                    return self.unpack_metadata_account_improved(
                        account_info.value.data
                    )
                else:
                    print("No metadata account found or account has no data")
                    return None

            except Exception as e:
                print(f"Error fetching metadata: {e}")
                return None

    def unpack_metadata_account_improved(self, data: bytes) -> dict | None:
        """
        Improved version with better error handling and documentation
        """
        try:
            # Validate input
            if not data:
                raise ValueError("No data provided")

            if len(data) < 50:  # Minimum reasonable size
                raise ValueError(f"Data too short: {len(data)} bytes")

            # Check account type
            if data[0] != 4:
                raise ValueError(f"Not a metadata account. Discriminator: {data[0]}")

            i = 1  # Start after discriminator

            # Parse fixed-length fields
            update_authority = base58.b58encode(data[i : i + 32])
            i += 32

            mint = base58.b58encode(data[i : i + 32])
            i += 32

            # Parse variable-length strings
            def parse_string():
                nonlocal i
                if i + 4 > len(data):
                    return ""
                length = struct.unpack("<I", data[i : i + 4])[0]
                i += 4
                if i + length > len(data):
                    return ""
                string_bytes = data[i : i + length]
                i += length
                return string_bytes.decode("utf-8", errors="ignore").strip("\x00")

            name = parse_string()
            symbol = parse_string()
            uri = parse_string()

            # Parse seller fee
            if i + 2 > len(data):
                fee = 0
            else:
                fee = struct.unpack("<h", data[i : i + 2])[0]
            i += 2

            # Parse creators
            creators = []
            verified = []
            share = []

            if i < len(data) and data[i]:  # has_creator flag
                i += 1
                if i + 4 <= len(data):
                    creator_len = struct.unpack("<I", data[i : i + 4])[0]
                    i += 4

                    for _ in range(creator_len):
                        if i + 34 <= len(
                            data
                        ):  # 32 bytes address + 1 verified + 1 share
                            creator = base58.b58encode(data[i : i + 32])
                            creators.append(creator)
                            i += 32

                            verified.append(data[i])
                            i += 1

                            share.append(data[i])
                            i += 1

            # Parse flags
            primary_sale_happened = bool(data[i]) if i < len(data) else False
            i += 1

            is_mutable = bool(data[i]) if i < len(data) else False

            return {
                "update_authority": update_authority.decode("utf-8"),
                "mint": mint.decode("utf-8"),
                "data": {
                    "name": name,
                    "symbol": symbol,
                    "uri": uri,
                    "seller_fee_basis_points": fee,
                    "creators": creators,
                    "verified": verified,
                    "share": share,
                },
                "primary_sale_happened": primary_sale_happened,
                "is_mutable": is_mutable,
            }

        except Exception as e:
            print(f"Error unpacking metadata: {e}")
            return None
