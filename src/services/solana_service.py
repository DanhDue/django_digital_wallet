import json

import base58
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID

from schemas.wallet_schemas import WalletModelCreationSchema, WalletModelSchema

LAMPORTS_PER_SOL = 1_000_000_000


class SolanaService:
    endpoint = "https://api.devnet.solana.com"

    @staticmethod
    def create_keypair_from_seed_bytes(seed_bytes: bytes) -> Keypair:
        return Keypair.from_seed(seed_bytes[:32])

    @staticmethod
    async def get_balance(address: str) -> float:
        async with AsyncClient(
            SolanaService.endpoint,
            timeout=30.0,
        ) as client:
            pubkey = Pubkey.from_string(address)
            response = await client.get_balance(pubkey)
            lamports = response.value
            return lamports / LAMPORTS_PER_SOL

    @staticmethod
    async def get_token_accounts(owner_address: str):
        async with AsyncClient(
            SolanaService.endpoint,
            timeout=30.0,
        ) as client:
            owner = Pubkey.from_string(owner_address)
            result = await client.get_token_accounts_by_owner_json_parsed(
                owner, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
            )
            accounts = [acc.account.data.parsed for acc in result.value]
            json_data = json.dumps(accounts, indent=2)
            return json_data

    @staticmethod
    def _create_wallet_model_from_keypair(
        keypair: Keypair, mnemonics: str | None = None
    ) -> WalletModelSchema:
        secret_bytes = bytes(keypair)
        return WalletModelSchema(
            bs58PrivateKey=base58.b58encode(secret_bytes).decode(),
            privateKey=str(list[int](secret_bytes)),
            address=str(keypair.pubkey()),
            mnemonics=mnemonics,
            balance=0,
        )

    @staticmethod
    def _restore_wallet_from_mnemonic(mnemonic: str) -> WalletModelSchema:
        try:
            seed_bytes = Bip39SeedGenerator(mnemonic).Generate("optional-passphrase")
            keypair = SolanaService.create_keypair_from_seed_bytes(seed_bytes)
            return SolanaService._create_wallet_model_from_keypair(keypair, mnemonic)
        except Exception as e:
            error_msg = (
                "Failed to parse mnemonic: Invalid mnemonic checksum."
                if "Invalid checksum" in str(e)
                else f"Failed to parse mnemonic: {e}"
            )
            return WalletModelSchema(error=error_msg)

    @staticmethod
    def _restore_wallet_from_private_key(private_key: str) -> WalletModelSchema:
        try:
            secret_key_bytes = bytes(json.loads(private_key))
            keypair = Keypair.from_bytes(secret_key_bytes)
            return SolanaService._create_wallet_model_from_keypair(keypair)
        except ValueError as e:
            print(f"Failed to parse secret key: {e}")
            return WalletModelSchema()

    @staticmethod
    def _restore_wallet_from_bs58_key(bs58_private_key: str) -> WalletModelSchema:
        try:
            keypair = Keypair.from_base58_string(bs58_private_key)
            return SolanaService._create_wallet_model_from_keypair(keypair)
        except Exception as e:
            print(f"Failed to parse bs58 private key: {e}")
            return WalletModelSchema()

    @staticmethod
    def _create_new_wallet() -> WalletModelSchema:
        generated_mnemonic = Bip39MnemonicGenerator().FromWordsNumber(24)
        seed_bytes = Bip39SeedGenerator(generated_mnemonic).Generate(
            "optional-passphrase"
        )
        keypair = SolanaService.create_keypair_from_seed_bytes(seed_bytes)
        return SolanaService._create_wallet_model_from_keypair(
            keypair, str(generated_mnemonic)
        )

    @staticmethod
    async def create_or_restore_wallet(
        data: WalletModelCreationSchema,
    ) -> WalletModelSchema:
        mnemonic = (data.mnemonics or "").strip()
        private_key = (data.privateKey or "").strip()
        bs58_private_key = (data.bs58PrivateKey or "").strip()

        if mnemonic:
            return SolanaService._restore_wallet_from_mnemonic(mnemonic)
        elif private_key:
            return SolanaService._restore_wallet_from_private_key(private_key)
        elif bs58_private_key:
            return SolanaService._restore_wallet_from_bs58_key(bs58_private_key)
        else:
            return SolanaService._create_new_wallet()

    @staticmethod
    async def verify_key_pair(pub_key: str, secret_key: str):
        pass

    @staticmethod
    async def validate_public_key(pub_key: str) -> bool:
        return True
