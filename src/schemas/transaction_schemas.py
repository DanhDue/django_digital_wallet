from typing import List, Optional
from ninja import Schema

from schemas.token_schemas import MintTokenSchema


class TransactionRetrieverSchema(Schema):
    # Account to be queried.
    account: str
    # Start searching backwards from this transaction signature.
    before_signature: Optional[str] = None
    # Search until this transaction signature, if found before limit reached.
    until_signature: Optional[str] = None
    # Maximum transaction signatures to return (between 1 and 1,000, default: 1,000).
    limit: Optional[int] = 10
    # Bank state to query. It can be either "finalized", "confirmed" or "processed".
    commitment: Optional[str] = None


class TransactionSchema(Schema):

    # Transaction signature (hash) as base58 string
    # This uniquely identifies the transaction on the Solana blockchain
    signature: Optional[str] = None
    
    # wallet address that owns the transaction and token accounts involved.
    owner: Optional[List[str]] = None

    # The Solana wallet address that will sent tokens.
    # Must be a valid base58-encoded Solana public key
    sender: Optional[str] = None

    # The Solana wallet address that pay network fee for sent tokens.
    # Must be a valid base58-encoded Solana public key
    payer: Optional[str] = None

    # The Solana wallet address that will receive tokens.
    # Must be a valid base58-encoded Solana public key
    recipient: Optional[str] = None

    # source_token_account
    source: Optional[str] = None

    # destination_token_account
    destination: Optional[str] = None

    # Current status of the transaction
    # Possible values: 'pending', 'confirmed', 'failed', 'expired'
    status: Optional[str] = None

    latest_blockhash: Optional[str] = None

    # Amount transferred in token(SOL or another like ZEO, USDT,...) units
    # This represents the net amount excluding fees
    amount: Optional[float] = None

    # total_cost = amount(Sol) + fee in SOL Units.
    total_sol: Optional[float] = None

    # total_cost = amount(Sol) + fee in LAMPORTS Units.
    total_lamports: Optional[int] = None

    # Transaction fee paid in SOL units
    # This is the network fee required to process the transaction
    fee_sol: Optional[float] = None

    # Transaction fee paid in LAMPORTS units
    # This is the network fee required to process the transaction
    fee_lamports: Optional[int] = None

    # Token account creation fee paid in SOL units
    # This is the network fee required to process the transaction
    token_account_creation_fee_sol: Optional[float] = None

    # Token account creation fee paid in LAMPORTS units
    # This is the network fee required to process the transaction
    token_account_creation_fee_lamports: Optional[int] = None

    # Token name (e.g., "Solana", "Zeno")
    # Full name of the token
    token: Optional[str] = None

    # Token symbol (e.g., "SOL", "ZEO")
    # For display purposes
    symbol: Optional[str] = None

    # SPL Token mint information
    # Contains details about the token contract
    mint_token: Optional[MintTokenSchema] = None

    # Direction of the transfer relative to the queried wallet
    # "in" for received, "out" for sent
    direction: Optional[str] = None  # SENT / RECEIVED

    # Block time when the transaction was confirmed
    # Unix timestamp in seconds
    timestamp: Optional[int] = None

    # Error message if the transaction failed
    # Only populated when status is 'failed' or 'error'
    error: Optional[str] = None

    required_for_dest_token_account_creation_fee: Optional[bool] = False

    def __hash__(self):
        return hash((self.signature, self.source))
