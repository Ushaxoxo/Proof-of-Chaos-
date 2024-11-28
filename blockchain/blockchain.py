from blockchain.block import Block
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

    def create_genesis_block(self):
        """
        Create the genesis block with default values.
        """
        genesis_block = Block(
            index=0,
            previous_hash="0",
            transactions=[],
            entropy="0",
            timestamp=time.time(),
        )
        genesis_block.hash = genesis_block.compute_hash()
        if self.logger:
            self.logger.info(f"Genesis Block Created: {genesis_block}")
        return genesis_block

    def add_transaction_to_pool(self, transaction):
        """
        Add a transaction to the global transaction pool.
        """
        self.pending_transactions.append(transaction)
        if self.logger:
            self.logger.info(f"Transaction added to pool: {transaction}")

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
