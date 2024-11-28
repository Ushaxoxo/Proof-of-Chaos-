from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.block import Block
from logger import setup_logger, log_transaction, log_block, log_error

# Set up logger
logger = setup_logger(name="BlockchainTest", log_file="test_blockchain.log", level="DEBUG")

def test_blockchain():
    try:
        # Step 1: Initialize Blockchain
        logger.info("Initializing Blockchain...")
        blockchain = Blockchain()

        # Step 2: Create Transactions
        logger.info("Creating Transactions...")
        transactions = [
            Transaction(sender="Alice", receiver="Bob", amount=50),
            Transaction(sender="Charlie", receiver="Dave", amount=100),
        ]
        for tx in transactions:
            log_transaction(logger, tx.to_dict())

        # Step 3: Create a Block
        logger.info("Creating and Adding a Block...")
        transaction_data = [tx.to_dict() for tx in transactions]
        new_block = Block(
            index=1,
            previous_hash=blockchain.chain[-1].hash,
            transactions=transaction_data,
            entropy="0.123456_0.654321",  # Dummy entropy for test purposes
        )
        blockchain.add_block(new_block)
        log_block(logger, new_block)

        # Step 4: Verify Blockchain Integrity
        logger.info("Verifying Blockchain Integrity...")
        assert len(blockchain.chain) == 2, "Blockchain should contain 2 blocks"
        assert blockchain.is_valid_block(new_block), "The new block should be valid"

        # Step 5: Handle Invalid Block
        logger.info("Testing Invalid Block Handling...")
        invalid_block = Block(
            index=2,
            previous_hash="INVALID_HASH",
            transactions=transaction_data,
            entropy="0.123456_0.654321",
        )
        try:
            blockchain.add_block(invalid_block)
        except Exception as e:
            logger.info(f"Invalid block rejected as expected: {str(e)}")

    except Exception as e:
        log_error(logger, str(e))


if __name__ == "__main__":
    test_blockchain()
