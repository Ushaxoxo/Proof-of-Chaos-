from flask import Flask, request, jsonify
from network.node import Node
from blockchain.blockchain import Blockchain
from blockchain.block import Block
from utils.logger import setup_logger
import os
from network.p2p import P2PNetwork
import time
import requests

# Flask App Initialization
app = Flask(__name__)

PEER_MAP = {
    "node1": ["http://pocnew1-node2-1:5000", "http://pocnew1-node3-1:5000", "http://pocnew1-node4-1:5000"],
    "node2": ["http://pocnew1-node1-1:5000", "http://pocnew1-node3-1:5000", "http://pocnew1-node4-1:5000"],
    "node3": ["http://pocnew1-node1-1:5000", "http://pocnew1-node2-1:5000", "http://pocnew1-node4-1:5000"],
    "node4": ["http://pocnew1-node1-1:5000", "http://pocnew1-node2-1:5000", "http://pocnew1-node3-1:5000"],
}



# Load Environment Variables
node_id = os.getenv("NODE_ID", "default_node")
log_file = os.getenv("LOG_FILE", f"logs/{node_id}.log")
port = int(os.getenv("PORT", 5000))  # Default to port 5000
peer_urls = PEER_MAP.get(node_id, [])

# Setup Logger
logger = setup_logger(name=node_id, log_file=log_file)
p2p_network = P2PNetwork(node_id=node_id, logger=logger)
p2p_network.peers = peer_urls

# Initialize Blockchain and Node
blockchain = Blockchain(logger=logger)
node = Node(node_id, blockchain, logger=logger, p2p_network=p2p_network)

if node.node_id == "node1":
    node.leader_id = "node1"
    node.is_leader = True
    p2p_network.broadcast_leader(node.leader_id)

else:
    node.leader_id = None
    node.is_leader = False


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """
    Add a transaction to the pool and synchronize it across nodes.
    """
    try:
        data = request.json
        if 'transaction' not in data:
            return jsonify({"error": "Transaction data missing"}), 400

        transaction = data['transaction']
        if node.add_transaction_to_pool(transaction):
            return jsonify({"message": "Transaction added and broadcasted successfully"}), 200
        else:
            return jsonify({"error": "Invalid transaction"}), 400
    except Exception as e:
        logger.error(f"Error in add_transaction: {str(e)}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/transaction_pool', methods=['GET'])
def get_transaction_pool():
    """
    Retrieve the current transaction pool.
    """
    try:
        transaction_pool = node.blockchain.pending_transactions
        return jsonify({"transaction_pool": transaction_pool}), 200
    except Exception as e:
        logger.error(f"Error in get_transaction_pool: {str(e)}")
        return jsonify({"error": "An error occurred while retrieving the transaction pool"}), 500

@app.route('/peers', methods=['GET'])
def get_peers():
    """
    Retrieve the list of peers connected to this node.
    """
    try:
        peers = node.p2p_network.peers
        return jsonify({"peers": peers}), 200
    except Exception as e:
        logger.error(f"Error in get_peers: {str(e)}")
        return jsonify({"error": "An error occurred while retrieving peers"}), 500

# @app.route('/generate_entropy', methods=['GET'])
# def generate_entropy():
#     """Generate and log entropy."""
#     entropy = node.generate_entropy()
#     return jsonify({"entropy": entropy}), 200


@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Retrieve the blockchain."""
    chain = [
        {
            "index": block.index,
            "previous_hash": block.previous_hash,
            "transactions": block.transactions,
            "entropy": block.entropy,
            "timestamp": block.timestamp,
            "hash": block.hash,
        }
        for block in blockchain.chain
    ]
    return jsonify(chain), 200

@app.route('/get_leader', methods=['GET'])
def get_leader():
    """
    Get the current leader node.
    """
    return jsonify({"leader": node.leader_id}), 200

@app.route('/set_leader', methods=['POST'])
def set_leader():
    """
    Set the leader node.
    """
    data = request.json
    if 'leader_id' not in data:
        return jsonify({"error": "Leader ID missing"}), 400

    leader_id = data['leader_id']
    node.leader_id = leader_id
    node.is_leader = (node.node_id == leader_id)
    node.logger.info(f"Leader updated to {leader_id}")
    return jsonify({"message": f"Leader updated to {leader_id}"}), 200

@app.route('/elect_leader', methods=['POST'])
def elect_leader():
    """
    Elect a new leader. Only the current leader can perform this action.
    """
    if not node.is_leader:
        return jsonify({"error": "Only the current leader can elect a new leader"}), 403

    data = request.json
    if 'new_leader_id' not in data:
        return jsonify({"error": "New leader ID missing"}), 400

    new_leader_id = data['new_leader_id']

    # Update leader information locally
    node.leader_id = new_leader_id
    node.is_leader = (node.node_id == new_leader_id)

    # Broadcast the new leader to all nodes
    if node.p2p_network:
        node.p2p_network.broadcast_leader(new_leader_id)

    return jsonify({"message": f"Leader changed to {new_leader_id}"}), 200

# @app.route('/send_entropy', methods=['POST'])
# def send_entropy():
#     """
#     Send the generated entropy to the leader node.
#     """
#     if not node.entropy:
#         return jsonify({"error": "Entropy not generated yet"}), 400

#     if node.leader_id == node.node_id:
#         return jsonify({"error": "This node is the leader and cannot send entropy to itself"}), 400

#     try:
#         leader_url = [peer for peer in node.p2p_network.peers if node.leader_id in peer][0]
#         response = requests.post(
#             f"{leader_url}/receive_entropy",
#             json={"node_id": node.node_id, "entropy": node.entropy},
#         )
#         return response.json(), response.status_code
#     except Exception as e:
#         node.logger.error(f"Failed to send entropy to leader: {str(e)}")
#         return jsonify({"error": "Failed to send entropy to leader"}), 500

@app.route('/receive_entropy', methods=['POST'])
def receive_entropy():
    """
    Receive entropy from another node.
    """
    if not node.is_leader:
        return jsonify({"error": "Only the leader can receive entropy"}), 403

    data = request.json
    node_id = data.get("node_id")
    entropy = data.get("entropy")

    if not node_id or entropy is None:
        return jsonify({"error": "Missing node_id or entropy"}), 400

    # Store the received entropy
    node.blockchain.node_entropies[node_id] = entropy
    node.logger.info(f"Received entropy from Node {node_id}: {entropy}")

    return jsonify({"message": f"Entropy from Node {node_id} received"}), 200


@app.route('/send_entropy', methods=['POST'])
def send_entropy():
    """
    Generate entropy and send it to the leader node.
    """
    # Step 1: Generate Entropy
    node.entropy = node.generate_entropy()
    if not node.entropy:
        node.logger.error("Failed to generate entropy.")
        return jsonify({"error": "Failed to generate entropy"}), 500

    # Step 2: Send Entropy to the Leader
    if node.leader_id == node.node_id:
        node.logger.error("This node is the leader and cannot send entropy to itself.")
        return jsonify({"error": "This node is the leader and cannot send entropy to itself"}), 400

    try:
        leader_url = [peer for peer in node.p2p_network.peers if node.leader_id in peer][0]
        response = requests.post(
            f"{leader_url}/receive_entropy",
            json={"node_id": node.node_id, "entropy": node.entropy},
        )
        if response.status_code == 200:
            node.logger.info(f"Successfully sent entropy to leader {node.leader_id}: {node.entropy}")
            return jsonify({"message": "Entropy generated and sent successfully"}), 200
        else:
            node.logger.error(f"Failed to send entropy to leader {node.leader_id}: {response.status_code}")
            return jsonify({"error": "Failed to send entropy to leader"}), response.status_code
    except Exception as e:
        node.logger.error(f"Error while sending entropy to leader: {str(e)}")
        return jsonify({"error": "Failed to send entropy to leader"}), 500


@app.route('/receive_aggregate_entropy', methods=['POST'])
def receive_aggregate_entropy():
    """
    Receive the aggregated entropy and update the next leader.
    """
    try:
        data = request.json
        aggregate_entropy = data.get("aggregate_entropy")
        next_leader = data.get("next_leader")

        if not aggregate_entropy or not next_leader:
            return jsonify({"error": "Missing aggregate_entropy or next_leader"}), 400

        # Update local state
        node.blockchain.aggregate_entropy = aggregate_entropy
        node.leader_id = next_leader
        node.is_leader = (node.node_id == next_leader)

        node.logger.info(f"Received aggregate_entropy: {aggregate_entropy}, Next leader: {next_leader}")
        return jsonify({"message": "Aggregate entropy and leader updated"}), 200
    except Exception as e:
        node.logger.error(f"Error in receive_aggregate_entropy: {str(e)}")
        return jsonify({"error": "Failed to process aggregate entropy"}), 500

@app.route('/aggregate_entropy', methods=['POST'])
def aggregate_entropy():
    """
    Aggregate entropy and determine the next leader.
    Only the current leader can perform this action.
    """
    if not node.is_leader:
        return jsonify({"error": "Only the leader can aggregate entropy"}), 403

    try:
        next_leader = node.calculate_aggregate_entropy_and_elect_leader()
        if next_leader:
            return jsonify({
                "message": "Aggregate entropy calculated and leader elected",
                "next_leader": next_leader
            }), 200
        else:
            return jsonify({"error": "Failed to calculate aggregate entropy"}), 500
    except Exception as e:
        node.logger.error(f"Error in aggregate_entropy: {str(e)}")
        return jsonify({"error": "An error occurred"}), 500
@app.route('/propose_block', methods=['POST'])
def propose_block():
    """
    Endpoint for the leader to propose a new block.
    """
    if not node.is_leader:
        node.logger.error(f"Node {node.node_id} is not the leader. Leader ID: {node.leader_id}")
        return jsonify({"error": "Only the leader can propose a block"}), 403

    try:
        # Debug: Log the type of aggregate_entropy
        node.logger.debug(f"Type of aggregate_entropy: {type(node.blockchain.aggregate_entropy)}")
        if isinstance(node.blockchain.aggregate_entropy, str):
            node.logger.error("aggregate_entropy is incorrectly a string. Investigate assignment conflicts.")

        # Ensure it is callable
        aggregated_entropy = node.blockchain.calculate_aggregate_entropy()
        new_block = node.propose_block(str(aggregated_entropy))

        if new_block:
            node.logger.info(f"Proposing block: {new_block.__dict__}")
            if node.p2p_network:
                node.p2p_network.broadcast_message(
                    "propose_block",
                    {
                        "index": new_block.index,
                        "previous_hash": new_block.previous_hash,
                        "transactions": new_block.transactions,
                        "entropy": new_block.entropy,
                        "timestamp": new_block.timestamp,
                        "hash": new_block.hash,
                        "block_data": new_block.__dict__,
                    }
                )
                node.blockchain.pending_block = new_block
                return jsonify({"message": "Block proposed and broadcasted", "block": new_block.__dict__}), 200
        else:
            return jsonify({"error": "Failed to propose a block"}), 500
    except Exception as e:
        node.logger.error(f"Error in propose_block: {str(e)}")
        return jsonify({"error": "Failed to propose a block"}), 500

@app.route('/receive_proposed_block', methods=['POST'])
def receive_proposed_block():
    """
    Follower nodes receive and validate a block proposed by the leader.
    """
    try:
        data = request.json
        node.logger.info(f"Received proposed block: {data}")

        # Extract and reconstruct the proposed block
        proposed_block = Block(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=data["transactions"],
            entropy=data["entropy"],
            timestamp=data["timestamp"],
        )
        proposed_block.hash = data["hash"]

        # Cache the received block for validation
        node.blockchain.pending_block = proposed_block

        # Validate the block
        is_valid = node.validate_block(proposed_block)

        # Respond to the leader with validation result
        response_status = "valid" if is_valid else "invalid"
        node.p2p_network.broadcast_message(
            "block_validation",
            {
                "block_index": proposed_block.index,
                "node_id": node.node_id,
                "status": response_status,
                "block_data": proposed_block.__dict__,  # Send block_data in the response
            }
        )

        return jsonify({"message": "Proposed block processed", "status": response_status}), 200
    except Exception as e:
        node.logger.error(f"Error in receive_proposed_block: {str(e)}")
        return jsonify({"error": "Failed to process proposed block"}), 500

@app.route('/validate_block', methods=['POST'])
def validate_block():
    """
    Endpoint to receive validation responses from other nodes.
    Ensures that each block is validated only once.
    """
    try:
        data = request.json
        block_index = data.get("block_index")
        node_id = data.get("node_id")
        status = data.get("status")
        block_data = data.get("block_data")  # Ensure block_data is retrieved

        if not block_index or not node_id or not status:
            node.logger.error(f"Invalid validation payload: {data}")
            return jsonify({"error": "Missing required fields"}), 400

        if not block_data:
            node.logger.error(f"Block data missing in payload: {data}")
            return jsonify({"error": "Block data missing"}), 400

        node.logger.info(f"Validation response received: Block {block_index}, Node {node_id}, Status {status}")

        # Ensure that validation happens only once for the given block
        if not hasattr(node, "processed_blocks"):
            node.processed_blocks = set()
        
        # Check if this block has already been processed
        if block_index in node.processed_blocks:
            node.logger.info(f"Block {block_index} has already been validated and processed. Ignoring.")
            return jsonify({"message": "Block already processed"}), 200

        # Track validation responses
        if not hasattr(node, "validation_responses"):
            node.validation_responses = {}
        if block_index not in node.validation_responses:
            node.validation_responses[block_index] = []
        node.validation_responses[block_index].append((status, block_data))  # Track status and block data

        # Check if majority validates
        valid_responses = [
            response for response in node.validation_responses[block_index] if response[0] == "valid"
        ]
        invalid_count = len([
            response for response in node.validation_responses[block_index] if response[0] == "invalid"
        ])
        total_nodes = len(node.p2p_network.peers) + 1  # Including the leader

        if len(valid_responses) > total_nodes // 2:
            # Retrieve block data from one of the valid responses
            block_data = valid_responses[0][1]
            block = Block(
                index=block_data["index"],
                previous_hash=block_data["previous_hash"],
                transactions=block_data["transactions"],
                entropy=block_data["entropy"],
                timestamp=block_data["timestamp"],
            )
            block.hash = block_data["hash"]  # Set the hash explicitly

            if node.blockchain.add_block(block):  # Use add_block method
                node.logger.info(f"Block successfully added to the chain: {block}")
                node.processed_blocks.add(block_index)  # Mark the block as processed
                del node.validation_responses[block_index]  # Clean up after success
                node.p2p_network.broadcast_message("blockchain_update", block.__dict__)

                return jsonify({"message": "Block added to blockchain"}), 200
            else:
                node.logger.error(f"Failed to add block to blockchain: {block}")
                return jsonify({"error": "Block validation succeeded but failed to add to chain"}), 500
        elif invalid_count > total_nodes // 2:
            node.logger.warning(f"Block {block_index} rejected by majority.")
            del node.validation_responses[block_index]
            node.processed_blocks.add(block_index)  # Mark the block as processed
            return jsonify({"message": "Block rejected"}), 200

        return jsonify({"message": "Waiting for more responses"}), 200
    except Exception as e:
        node.logger.error(f"Error in validate_block: {str(e)}")
        return jsonify({"error": "Failed to process validation"}), 500

@app.route('/blockchain_update', methods=['POST'])
def blockchain_update():
    try:
        data = request.json
        block = Block(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=data["transactions"],
            entropy=data["entropy"],
            timestamp=data["timestamp"],
        )
        block.hash = data["hash"]

        if node.blockchain.add_block(block):
            node.logger.info(f"Blockchain updated with block {block.index}.")
            return jsonify({"message": "Blockchain updated"}), 200
        else:
            node.logger.warning(f"Failed to update blockchain with block {block.index}.")
            return jsonify({"error": "Failed to update blockchain"}), 500
    except Exception as e:
        node.logger.error(f"Error in blockchain_update: {str(e)}")
        return jsonify({"error": "Failed to update blockchain"}), 500


if __name__ == "__main__":
    print(f"Starting Flask app on port {port} for node {node_id}")

    app.run(host="0.0.0.0",port=5000)



