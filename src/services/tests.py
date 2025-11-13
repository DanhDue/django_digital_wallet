from django.test import TestCase
from services.solana_service import SolanaService

class SolanaServiceTest(TestCase):
    def setUp(self):
        self.solana_service = SolanaService()

    def test_restore_wallet_from_mnemonic_none(self):
        result = self.solana_service._restore_wallet_from_mnemonic(None)
        self.assertIsNotNone(result.error)
        self.assertIn("Mnemonic cannot be None.", result.error)

    def test_restore_wallet_from_bs58_key_none(self):
        result = self.solana_service._restore_wallet_from_bs58_key(None)
        self.assertIsNotNone(result.error)
        self.assertIn("bs58 private key cannot be None.", result.error)
