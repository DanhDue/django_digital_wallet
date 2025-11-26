from typing import Any, Dict
from enum import Enum


class TransactionType(Enum):
    SOL_TRANSFER = "SOL_TRANSFER"
    SPL_TOKEN_TRANSFER = "SPL_TOKEN_TRANSFER"
    SPL_TOKEN_TRANSFER_WITH_TOKEN_ACCOUNT_CREATION = (
        "SPL_TOKEN_TRANSFER_WITH_TOKEN_ACCOUNT_CREATION"
    )
    SWAP = "SWAP"
    SWAP_WITH_TOKEN_ACCOUNT_CREATION = "SWAP_WITH_TOKEN_ACCOUNT_CREATION"
    STAKE = "STAKE"
    CREATE_TOKEN_ACCOUNT = "CREATE_TOKEN_ACCOUNT"
    UNKNOWN = "UNKNOWN"


class SolanaTransactionClassifier:
    def __init__(self):
        # Mapping common program IDs to transaction types
        self.program_mapping = {
            # System / SOL Transfer
            "11111111111111111111111111111111": TransactionType.SOL_TRANSFER,
            # SPL Token
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": TransactionType.SPL_TOKEN_TRANSFER,
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": TransactionType.CREATE_TOKEN_ACCOUNT,
            # DEXs & Swaps
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": TransactionType.SWAP,
            "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": TransactionType.SWAP,  # Orca
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": TransactionType.SWAP,  # Raydium
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": TransactionType.SWAP,  # Jupiter
            "JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo": TransactionType.SWAP,  # Jupiter V2
            "JUP3c2Uh3WA4Ng34tw6kPd2G4C5BB21Xo36Je1s32Ph": TransactionType.SWAP,  # Jupiter V3
            "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLRkjjjgv2kWFfg": TransactionType.SWAP,  # Phoenix
            # Staking
            "Stake11111111111111111111111111111111111111": TransactionType.STAKE,
            "SysvarStakeHistory1111111111111111111111111": TransactionType.STAKE,
        }

        # Swap instruction keywords
        self.swap_instructions = {"swap", "swapV2", "route", "exchange"}

        # Transfer instruction keywords
        self.transfer_instructions = {"transfer", "transferChecked"}

        # Create token account instruction keywords
        self.create_account_instructions = {
            "initializeAccount",
            "initializeAccount2",
            "initializeAccount3",
            "createAccount",
            "createAssociatedTokenAccount",
        }

    def get_transaction_type(self, transaction_data: Dict[str, Any]) -> TransactionType:
        """
        Returns transaction type as one of:
        - "transfer sol"
        - "spl token transfer"
        - "swap"
        - "stake"
        - "create token account"
        - "unknown"
        """
        try:
            # Get transaction details
            tx_info = transaction_data.get("result", {})
            message = tx_info.get("transaction", {}).get("message", {})
            meta = tx_info.get("meta", {})
            instructions = message.get("instructions", [])
            inner_instructions = meta.get("innerInstructions", [])
            log_messages = meta.get("logMessages", [])

            # Collect all instructions
            all_instructions = list(instructions)
            for inner in inner_instructions:
                all_instructions.extend(inner.get("instructions", []))

            # Check instruction types and log messages for swaps
            if self._is_swap_transaction(all_instructions, log_messages):
                return (
                    TransactionType.SWAP_WITH_TOKEN_ACCOUNT_CREATION
                    if self._is_create_token_account(all_instructions, log_messages)
                    else TransactionType.SWAP
                )

            # Check for SPL token transfers
            if self._is_spl_token_transfer(all_instructions):
                with_token_account_creation = self._is_create_token_account(
                    all_instructions, log_messages
                )
                if with_token_account_creation:
                    return (
                        TransactionType.SPL_TOKEN_TRANSFER_WITH_TOKEN_ACCOUNT_CREATION
                    )
                return TransactionType.SPL_TOKEN_TRANSFER

            # Check for create token account first (has highest priority for detection)
            if self._is_create_token_account(all_instructions, log_messages):
                return TransactionType.CREATE_TOKEN_ACCOUNT

            # Check programs
            program_ids = set()
            for instr in all_instructions:
                program_id = instr.get("programId", "")
                program_ids.add(program_id)

            # Check for staking
            if self._is_stake_transaction(program_ids, all_instructions):
                return TransactionType.STAKE

            # Check for SOL transfers
            if self._is_sol_transfer(all_instructions, program_ids):
                return TransactionType.SOL_TRANSFER

            return TransactionType.UNKNOWN

        except Exception as e:
            print(f"Error classifying transaction: {e}")
            return TransactionType.UNKNOWN

    def _is_create_token_account(self, instructions: list, log_messages: list) -> bool:
        """Check if transaction is creating a token account"""
        # Check log messages for create account keywords
        for log in log_messages:
            log_lower = log.lower()
            if any(
                keyword in log_lower
                for keyword in [
                    "initializeaccount",
                    "createaccount",
                    "associatedtokenaccount",
                ]
            ):
                return True
            if "instruction: initializeaccount" in log_lower:
                return True
            if "instruction: create" in log_lower and "account" in log_lower:
                return True

        # Check instructions for create account operations
        for instr in instructions:
            program_id = instr.get("programId", "")

            # Associated Token Account Program
            if program_id == "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL":
                return True

            # Check parsed instructions for create/initialize operations
            if "parsed" in instr:
                instr_type = instr["parsed"].get("type", "").lower()
                if any(
                    keyword in instr_type
                    for keyword in self.create_account_instructions
                ):
                    return True

                # Also check info for account creation patterns
                info = instr["parsed"].get("info", {})
                if "newAccount" in info or "account" in info:
                    return True

            # Check SPL Token program for initialize operations
            if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                if "parsed" in instr:
                    instr_type = instr["parsed"].get("type", "").lower()
                    if "initialize" in instr_type:
                        return True

        return False

    def _is_swap_transaction(self, instructions: list, log_messages: list) -> bool:
        """Check if transaction is a swap"""
        # Check log messages for swap keywords
        for log in log_messages:
            log_lower = log.lower()
            if any(keyword in log_lower for keyword in self.swap_instructions):
                return True
            if "instruction: swap" in log_lower:
                return True

        # Check instruction data for swap patterns
        for instr in instructions:
            # Check parsed instructions
            if "parsed" in instr:
                instr_type = instr["parsed"].get("type", "").lower()
                if any(keyword in instr_type for keyword in self.swap_instructions):
                    return True

            # Check program ID for known DEXs
            program_id = instr.get("programId", "")
            if program_id in [
                pid
                for pid, tx_type in self.program_mapping.items()
                if tx_type == "swap"
            ]:
                return True

        return False

    def _is_spl_token_transfer(self, instructions: list) -> bool:
        """Check if transaction is SPL token transfer"""
        for instr in instructions:
            if "parsed" in instr:
                instr_type = instr["parsed"].get("type", "").lower()
                if any(keyword in instr_type for keyword in self.transfer_instructions):
                    return True
        return False

    def _is_sol_transfer(self, instructions: list, program_ids: set) -> bool:
        """Check if transaction is SOL transfer"""
        # SOL transfer uses system program
        if "11111111111111111111111111111111" in program_ids:
            for instr in instructions:
                if instr.get("programId") == "11111111111111111111111111111111":
                    if "parsed" in instr and instr["parsed"].get("type") == "transfer":
                        return True
        return False

    def _is_stake_transaction(self, program_ids: set, instructions: list) -> bool:
        """Check if transaction is staking related"""
        stake_programs = {"Stake11111111111111111111111111111111111111"}

        if any(pid in stake_programs for pid in program_ids):
            return True

        # Check for staking instructions
        for instr in instructions:
            if "parsed" in instr:
                instr_type = instr["parsed"].get("type", "").lower()
                if instr_type in {"delegate", "deactivate", "withdraw", "split"}:
                    return True

        return False
