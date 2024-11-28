from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from network.node import Node
from utils.logger import setup_logger, log_transaction, log_block, log_entropy, log_error
from network.p2p import P2PNetwork

def main():
    # Step 1: Set up Logger
    logger = setup_logger(name="BlockchainSystem", log_file="blockchain_system.log", level="DEBUG")
    logger.info("=== Starting Blockchain System ===")

    try:
        # Step 2: Initialize Blockchain
        logger.info("Initializing Blockchain...")
        blockchain = Blockchain(logger=logger)

        # Step 3: Create Nodes
        logger.info("Creating Nodes...")
        nodes = [Node(f"Node_{i}", blockchain) for i in range(5)]  # Simulate 5 nodes
        blockchain.nodes = nodes  # Attach nodes to the blockchain instance
        logger.info(f"Created {len(nodes)} nodes: {[node.node_id for node in nodes]}")

        # Step 3.1: Set Node_0 as the initial leader
        current_leader = "Node_0"
        leader_node = next(node for node in nodes if node.node_id == current_leader)
        leader_node.is_leader = True  # Set the initial leader
        logger.info(f"Node_0 is set as the initial leader.")

        # Generate entropy for each node and send it to the leader
        logger.info("Generating and sending entropy for all nodes...")
        for node in nodes:
            node.entropy = node.generate_entropy()
            log_entropy(logger, node.node_id, node.entropy)
            if not node.is_leader:  # Skip sending entropy for the leader node
                node.send_entropy_to_leader(leader_node)

        # Step 4: Add Transactions to the Pools
        logger.info("Adding Transactions to the Pools...")
        transactions = [
            {"sender": "Alice", "receiver": "Bob", "amount": 50},
            {"sender": "Charlie", "receiver": "Dave", "amount": 100},
            {"sender": "Eve", "receiver": "Frank", "amount": 200},
            {"sender": "Grace", "receiver": "Hank", "amount": 75},
            {"sender": "Ivy", "receiver": "John", "amount": 125},
            # Add more transactions as needed
        ]

        for tx in transactions:
            blockchain.add_transaction_to_pool(tx)  # Add to blockchain's global pool
            for node in nodes:
                node.add_transaction_to_pool(tx)  # Add to each node's local pool
            log_transaction(logger, tx)
        logger.info(f"{len(transactions)} transactions added to the pools of all nodes.")

        # Step 5: Initialize P2P Network for Communication
        logger.info("Setting up P2P Network...")
        p2p_network = P2PNetwork(node_id="Node_0", host="localhost", port=8000)
        p2p_network.start()
        logger.info("P2P Network initialized and listening on localhost:8000")

        # Step 6: Perform Proof of Chaos Consensus
        logger.info("Performing Proof of Chaos Consensus...")

        # Step 6.1: Current Leader Calculates and Broadcasts Aggregated Entropy
        logger.info(f"Leader {current_leader} is calculating and broadcasting aggregated entropy...")
        aggregated_entropy = leader_node.calculate_and_broadcast_entropy(p2p_network)

        # Step 6.2: Elect the New Leader
        logger.info("Electing a new leader based on aggregated entropy...")
        next_leader = blockchain.elect_new_leader(aggregated_entropy)
        logger.info(f"New Leader Elected: {next_leader}")

        # Update leader status
        leader_node.is_leader = False
        new_leader_node = next(node for node in nodes if node.node_id == next_leader)
        new_leader_node.is_leader = True

        # Step 6.3: New Leader Proposes a Block
        logger.info(f"{next_leader} is proposing a block...")
        transactions_for_block = new_leader_node.get_transactions_from_pool(limit=50)  # Get transactions from the node's pool
        new_block = new_leader_node.propose_block(aggregated_entropy)
        logger.info(f"Proposed Block by {next_leader}: Index {new_block.index}, Hash {new_block.hash}")

        # Step 6.4: Validate the Block
        logger.info("Validating the proposed block across all nodes...")
        validation_results = [
            node.validate_block(new_block) for node in nodes
        ]
        validation_count = sum(validation_results)

        # Check if majority validated the block
        threshold = len(nodes) // 2 + 1  # Majority threshold
        majority_valid = validation_count >= threshold

        if majority_valid:
            logger.info(f"Block validated successfully by {validation_count}/{len(nodes)} nodes. Adding to blockchain.")
            blockchain.add_block(new_block)
            log_block(logger, new_block)
            logger.info("Block added successfully.")
        else:
            logger.error(f"Block validation failed. Only {validation_count}/{len(nodes)} nodes validated the block. Block will not be added.")

        # Step 6.5: Update Reputation Scores
        logger.info("Updating reputation scores for all nodes...")
        for i, node in enumerate(nodes):
            node.update_reputation(
                is_valid=validation_results[i],
                majority_valid=majority_valid,
                is_leader=node.is_leader,
                block_accepted=majority_valid if node.is_leader else None,
            )

        # Step 7: Verify Blockchain State
        logger.info("Verifying Blockchain State...")
        for block in blockchain.chain:
            logger.info(f"Block {block.index}: {block}")

    except Exception as e:
        log_error(logger, f"An error occurred: {str(e)}")
        logger.error("Blockchain System encountered a critical error and stopped.")

if __name__ == "__main__":
    main()
