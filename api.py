from flask import Flask, request, jsonify
from network.node import Node
from blockchain.blockchain import Blockchain
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
        transaction_pool = blockchain.pending_transactions
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


if __name__ == "__main__":
    print(f"Starting Flask app on port {port} for node {node_id}")

    app.run(host="0.0.0.0",port=5000)



