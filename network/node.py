from blockchain.consensus import henon_entropy, reorder_transactions, weighted_minkowski_distance, entropy_to_numeric
from blockchain.block import Block
from utils.logger import setup_logger
import random
import requests 

node_logger = setup_logger(name="BlockchainNode", log_file="blockchain_system.log", level="DEBUG")

def leader_only(func):
    def wrapper(self, *args, **kwargs):
        if not self.is_leader:
            raise PermissionError(f"Node {self.node_id} is not the leader and cannot execute {func.__name__}.")
        return func(self, *args, **kwargs)
    return wrapper

class Node:
    def __init__(self, node_id, blockchain,logger=None,p2p_network=None):
        self.node_id = node_id
        self.blockchain = blockchain
        self.logger = logger or setup_logger(name=node_id)  # Use provided logger or default
        self.transaction_pool = []  # Local transaction pool
        self.entropy = None  # Node-specific entropy
        self.is_leader = False  # Indicates if the node is the leader
        self.leader_id = None  # Track the current leader ID
        self.reputation_score = 50  # Default reputation score for the node
        self.p2p_network = p2p_network  # Reference to the P2P network instance
        self.processed_transactions = set()  # Track processed transaction IDs
        self.processed_blocks = set()  # Track processed block indices (to prevent reprocessing)
        self.validation_responses = {}  # Store validation responses for each block index

        print(f"Node {self.node_id} initialized.")  # Debug print

        if self.logger:
            self.logger.info(f"Node {self.node_id} initialized.")
        if hasattr(blockchain, "aggregate_entropy"):
            self.logger.debug(f"Type of blockchain.aggregate_entropy: {type(blockchain.aggregate_entropy)}")
            if isinstance(blockchain.aggregate_entropy, str):
                self.logger.error("aggregate_entropy is incorrectly a string. Investigate assignment conflicts.")

    def generate_entropy(self):
        """
        Generate entropy using the Henon Map from consensus.py.
        """
        self.entropy = henon_entropy()
        if self.logger:
            self.logger.debug(f"Node {self.node_id} generated entropy: {self.entropy}")
        return self.entropy

    def send_entropy_to_leader(self, leader_node):
        """
        Send entropy to the leader node.
        """
        leader_node.receive_entropy(self.node_id, self.entropy)
        if self.logger:
            self.logger.info(f"Node {self.node_id} sent entropy to leader {leader_node.node_id}")

    def receive_entropy(self, node_id, entropy):
        """
        Receive entropy from another node.
        """
        try:
            numeric_entropy = entropy_to_numeric(entropy)  # Convert to numeric format
            self.blockchain.node_entropies[node_id] = numeric_entropy
            if self.logger:
                self.logger.info(f"Leader {self.node_id} received entropy from Node {node_id}: {entropy}")
        except Exception as e:
            self.logger.error(f"Failed to process entropy from Node {node_id}: {str(e)}")

    def add_transaction_to_pool(self, transaction):
        """
        Add a transaction to the pool if it hasn't already been processed.
        """
        transaction_id = transaction.get("id")
        
        # Check if the transaction has already been processed
        if transaction_id in self.processed_transactions:
            self.logger.info(f"Transaction {transaction_id} already processed. Skipping.")
            return False

        # Add the transaction to the blockchain's transaction pool
        if self.blockchain.add_transaction_to_pool(transaction):
            # Mark the transaction as processed
            self.processed_transactions.add(transaction_id)

            # Add the transaction to the local transaction pool
            self.transaction_pool.append(transaction)
            
            # Log and broadcast the transaction
            self.logger.info(f"Transaction {transaction_id} added to the pool: {transaction}")
            if self.p2p_network:
                self.logger.info(f"Broadcasting transaction: {transaction}")
                self.p2p_network.broadcast_transaction(transaction)

            return True

        return False


    def get_transactions_from_pool(self, limit=50):
        """
        Retrieve a limited number of transactions from the pool.
        """
        return self.transaction_pool[:limit]
    
    def remove_transactions_from_pool(self, transactions):
        """
        Remove transactions from the transaction pool.
        :param transactions: List of transactions to remove
        """
        try:
            transaction_ids = {tx["id"] for tx in transactions}
            self.blockchain.pending_transactions = [
                tx for tx in self.blockchain.pending_transactions
                if tx["id"] not in transaction_ids
            ]
            self.logger.info(f"Removed transactions from pool: {transaction_ids}")
        except Exception as e:
            self.logger.error(f"Error removing transactions from pool: {str(e)}")


    # @leader_only
    # def calculate_and_broadcast_entropy(self, p2p_network):
    #     """
    #     Calculate the aggregated entropy and broadcast it to the network.
    #     """
    #     if not self.blockchain.node_entropies:
    #         self.logger.error("No entropy values received from nodes. Cannot calculate aggregated entropy.")
    #         return None

    #     # Calculate aggregated entropy
    #     aggregated_entropy = self.blockchain.aggregate_entropy()

    #     # Log and broadcast the aggregated entropy
    #     self.logger.info(f"Node {self.node_id} calculated Aggregated Entropy: {aggregated_entropy}")
    #     p2p_network.broadcast_entropy(aggregated_entropy)
    #     self.logger.info(f"Node {self.node_id} broadcasted Aggregated Entropy: {aggregated_entropy}")

    #     return aggregated_entropy

    
    @leader_only
    def propose_block(self, aggregated_entropy):
            """
            Propose a new block if this node is the leader.
            """
            try:
                # Fetch transactions from the transaction pool
                transactions = self.get_transactions_from_pool(limit=50)
                if not transactions:
                    self.logger.warning("No transactions available to include in the block.")
                    return None

                # Log the transaction pool and aggregated entropy
                self.logger.debug(f"Transactions in pool: {transactions}")
                self.logger.debug(f"Aggregated entropy: {aggregated_entropy}")

                # Reorder transactions
                ordered_transactions = reorder_transactions(transactions, str(aggregated_entropy), logger=self.logger)

                # Create the new block
                new_block = Block(
                    index=len(self.blockchain.chain),
                    previous_hash=self.blockchain.chain[-1].hash,
                    transactions=ordered_transactions,
                    entropy=str(aggregated_entropy),
                )
                new_block.hash = new_block.compute_hash()

                # Remove processed transactions from the pool
                self.remove_transactions_from_pool(transactions)

                # Log the proposed block
                self.logger.info(f"Proposed Block: {new_block}")
                return new_block

            except Exception as e:
                self.logger.error(f"Error in propose_block: {str(e)}")
                return None


    def __repr__(self):
        return f"Node(ID: {self.node_id}, Leader: {self.is_leader})"

    def validate_block(self, block):
        """
        Validate a block using the transaction pool and consensus rules.
        :param block: Block to validate.
        :return: True if the block is valid, False otherwise.
        """
        self.logger.info(f"Node {self.node_id} validating Block {block.index} with aggregate entropy {block.entropy}")

        # Check the previous hash
        if block.previous_hash != self.blockchain.chain[-1].hash:
            self.logger.error(f"Validation failed: Previous hash mismatch. Expected {self.blockchain.chain[-1].hash}, Found {block.previous_hash}")
            return False

        # Retrieve transactions from the pool
        transactions_from_pool = self.get_transactions_from_pool(limit=50)

        try:
            # Reorder transactions using the block's entropy
            reordered_transactions = reorder_transactions(transactions_from_pool, block.entropy, logger=self.logger)

            # Compare reordered transactions with block transactions
            if reordered_transactions != block.transactions:
                self.logger.error("Validation failed: Transaction order mismatch.")
                self.logger.error(f"Expected order: {reordered_transactions}")
                self.logger.error(f"Block order: {block.transactions}")
                return False
        except Exception as e:
            self.logger.error(f"Validation failed during transaction reordering: {e}")
            return False

        # Check block entropy
        if block.entropy is None:
            self.logger.error("Validation failed: Block entropy is None.")
            return False

        # Check block hash
        computed_hash = block.compute_hash()
        if block.hash != computed_hash:
            self.logger.error("Validation failed: Block hash mismatch.")
            self.logger.error(f"Computed hash: {computed_hash}")
            self.logger.error(f"Block hash: {block.hash}")
            return False

        self.logger.info(f"Node {self.node_id} successfully validated Block {block.index}.")
        return True
    
    def update_reputation(self, is_valid, majority_valid, is_leader=False, block_accepted=False):
        """
        Update the reputation score based on how the node's validation aligns with the majority.
        Also updates the reputation for the leader based on block acceptance or rejection.

        :param is_valid: Boolean indicating whether the node's validation decision.
        :param majority_valid: Boolean indicating the majority decision.
        :param is_leader: Boolean indicating if the node is the leader.
        :param block_accepted: Boolean indicating if the block proposed by the leader was accepted.
        """
        # For validators: reward/penalize for alignment with the majority
        if not is_leader:
            if is_valid == majority_valid:
                self.reputation_score += 5  # Reward for aligning with the majority
            else:
                self.reputation_score -= 5  # Penalize for misalignment

        # For the leader: reward/penalize based on block acceptance
        if is_leader:
            if block_accepted:
                self.reputation_score += 10  # Reward for proposing a valid block
                self.logger.info(f"Leader Node {self.node_id}: Block accepted. Reputation Score increased to {self.reputation_score}.")
            else:
                self.reputation_score -= 10  # Penalize for proposing an invalid block
                self.logger.info(f"Leader Node {self.node_id}: Block rejected. Reputation Score decreased to {self.reputation_score}.")
        
        self.logger.info(f"Node {self.node_id}: Reputation Score updated to {self.reputation_score}.")

    @leader_only
    def calculate_aggregate_entropy_and_elect_leader(self):
        """
        Leader aggregates entropy from all nodes, determines the next leader,
        and broadcasts both the aggregate entropy and the new leader.
        """
        if not self.blockchain.node_entropies:
            self.logger.error("No entropy values received from nodes. Cannot calculate aggregate entropy.")
            return None

        # Calculate aggregated entropy
        aggregated_entropy = self.blockchain.calculate_aggregate_entropy()
        self.logger.info(f"Aggregated entropy: {aggregated_entropy}")

        try:
            # Convert aggregate entropy to numeric
            next_entropy = entropy_to_numeric(aggregated_entropy)

            # Determine the next leader
            closest_node = None
            closest_distance = float('inf')

            for node_id, node_entropy in self.blockchain.node_entropies.items():
                numeric_entropy = entropy_to_numeric(node_entropy)  # Convert each entropy to numeric
                distance = weighted_minkowski_distance(next_entropy, numeric_entropy)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_node = node_id

            # Update the leader
            self.logger.info(f"Aggregate entropy: {aggregated_entropy}, Next leader: {closest_node}")
            self.leader_id = closest_node
            self.is_leader = (self.node_id == closest_node)

            # Broadcast the new leader and aggregate entropy
            if self.p2p_network:
                self.p2p_network.broadcast_message(
                    "broadcast_aggregate_entropy",
                    {"aggregate_entropy": aggregated_entropy, "next_leader": closest_node}
                )

            return closest_node

        except Exception as e:
            self.logger.error(f"Error in calculate_aggregate_entropy_and_elect_leader: {str(e)}")
            return None


   
    def broadcast_entropy(self):
        """
        Broadcast the generated entropy to the leader.
        """
        if self.leader_id == self.node_id:
            self.logger.warning("This node is the leader. Cannot broadcast entropy to itself.")
            return

        leader_url = [peer for peer in self.p2p_network.peers if self.leader_id in peer][0]

        try:
            response = requests.post(
                f"{leader_url}/receive_entropy",
                json={"node_id": self.node_id, "entropy": self.entropy},
            )
            self.logger.info(f"Entropy sent to leader {self.leader_id}. Response: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to send entropy to leader {self.leader_id}: {str(e)}")
