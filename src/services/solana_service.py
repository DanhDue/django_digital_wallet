import json
from typing import Any

import base58
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID

LAMPORTS_PER_SOL = 1_000_000_000


class SolanaService:
    endpoint = "https://api.devnet.solana.com"

    @staticmethod
    def keypair_from_seed_bytes(seed_bytes: bytes) -> Keypair:
        """Create a Keypair from BIP39 seed bytes (use first 32 bytes)."""
        return Keypair.from_seed(seed_bytes[:32])

    @staticmethod
    async def get_balance(address: str) -> float:
        """Get balance (in SOL) for a wallet address."""
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
        """List token accounts owned by a wallet."""
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
    async def create_or_restore_wallet():
        mnemonic = Bip39MnemonicGenerator().FromWordsNumber(24)
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate("optional-passphrase")
        keypair = SolanaService.keypair_from_seed_bytes(seed_bytes)
        secret_bytes = bytes(keypair)
        private_key_bytes = secret_bytes[:32]
        secret_uint8array = list[Any](keypair.secret())
        result = {
            "mnemonic": str(mnemonic),
            "bs58PrivateKey": base58.b58encode(private_key_bytes).decode(),
            "private_key": str(secret_uint8array),
            "public_key": f"{keypair.pubkey()}",
        }
        return result
