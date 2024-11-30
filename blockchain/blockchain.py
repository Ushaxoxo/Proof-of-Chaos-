from blockchain.block import Block
from config import GENESIS_BLOCK
from blockchain.consensus import (
    weighted_average_fusion,
    weighted_minkowski_distance,
    entropy_to_numeric,
)
from utils.logger import setup_logger, log_transaction, log_block, log_entropy, log_error
import time

class Blockchain:
    def __init__(self, logger=None):
        self.logger = logger
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []  # Global transaction pool
        self.node_entropies = {}  # Dictionary to store node_id -> entropy
        self.received_entropy = None  # Initialize received entropy
        self.nodes = []  # List of nodes in the blockchain system
        self.validate_genesis_block()

    def create_genesis_block(self):
        """
        Create the shared genesis block using pre-defined values.
        """
        genesis_block = Block(
            index=GENESIS_BLOCK["index"],
            previous_hash=GENESIS_BLOCK["previous_hash"],
            transactions=GENESIS_BLOCK["transactions"],
            entropy=GENESIS_BLOCK["entropy"],
            timestamp=GENESIS_BLOCK["timestamp"],
        )
        genesis_block.hash = GENESIS_BLOCK["hash"]
        if self.logger:
            self.logger.info(f"Genesis Block Created: {genesis_block}")
        return genesis_block

    def validate_genesis_block(self):
        """
        Ensure the Genesis Block matches the shared Genesis Block.
        """
        genesis_block = self.chain[0]
        if (
            genesis_block.index != GENESIS_BLOCK["index"]
            or genesis_block.previous_hash != GENESIS_BLOCK["previous_hash"]
            or genesis_block.hash != GENESIS_BLOCK["hash"]
            or genesis_block.transactions != GENESIS_BLOCK["transactions"]
            or genesis_block.entropy != GENESIS_BLOCK["entropy"]
            or abs(genesis_block.timestamp - GENESIS_BLOCK["timestamp"]) > 1e-6
        ):
            raise ValueError("Genesis Block mismatch! Check configuration.")

    def add_transaction_to_pool(self, transaction):
        if self.validate_transaction(transaction):
            self.pending_transactions.append(transaction)
            if self.logger:
                self.logger.info(f"Transaction added to pool: {transaction}")
            return True
        else:
            if self.logger:
                self.logger.warning(f"Invalid transaction rejected: {transaction}")
            return False
        
    def validate_transaction(self, transaction):
        """
        Validate a transaction (basic validation for now).
        """
        # Add specific validation logic (e.g., format, signature)
        return isinstance(transaction, dict) and "id" in transaction and "data" in transaction

    def get_transactions_from_pool(self, limit=50):
        """
        Retrieve a limited number of transactions from the pool.
        """
        return self.pending_transactions[:limit]

    def remove_transactions_from_pool(self, transactions):
        """
        Remove transactions from the pool after they are included in a block.
        """
        self.pending_transactions = [
            tx for tx in self.pending_transactions if tx not in transactions
        ]
        if self.logger:
            self.logger.info(f"Removed {len(transactions)} transactions from the pool.")

    def add_block(self, block):
        """
        Add a block to the chain after validation.
        """
        self.chain.append(block)
        self.remove_transactions_from_pool(block.transactions)
        if self.logger:
            self.logger.info(f"Block {block.index} added to the blockchain.")

    def aggregate_entropy(self):
        """
        Aggregate entropy using weighted average fusion.
        """
        aggregated_entropy = weighted_average_fusion(self.node_entropies)
        if self.logger:
            self.logger.info(f"Aggregated Entropy: {aggregated_entropy}")
        return f"{aggregated_entropy:.6f}"

    def elect_new_leader(self, aggregated_entropy):
        """
        Elect a new leader based on proximity to the aggregated entropy.
        """
        self.logger.info(f"Electing a new leader based on Aggregated Entropy: {aggregated_entropy}")

        closest_node = None
        closest_proximity = float("inf")

        for node_id, entropy in self.node_entropies.items():
            proximity = weighted_minkowski_distance(
                entropy_to_numeric(entropy),
                entropy_to_numeric(aggregated_entropy),
            )
            self.logger.info(f"Node {node_id} proximity to Aggregated Entropy: {proximity}")

            if proximity < closest_proximity:
                closest_proximity = proximity
                closest_node = node_id

        if closest_node:
            # Update leader flags
            for node in self.nodes:
                if node.node_id == closest_node:
                    node.is_leader = True
                    self.logger.info(f"Node {node.node_id} is now the leader.")
                else:
                    if node.is_leader:  # Log if the old leader is being demoted
                        self.logger.info(f"Node {node.node_id} is no longer the leader.")
                    node.is_leader = False

        self.logger.info(f"New Leader Elected: {closest_node} with proximity {closest_proximity}")
        return closest_node
