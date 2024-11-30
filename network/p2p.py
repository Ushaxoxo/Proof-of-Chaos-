import json
import threading
import socket
from utils.logger import setup_logger
import requests 
import time
class P2PNetwork:
    
    def __init__(self, node_id, host="localhost", port=5000,logger=None):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.logger = logger

        self.peers = []  # List of connected peers (host, port)
        self.handlers = {}  # Message type -> handler function
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.register_handler("broadcast_entropy", self.handle_broadcast_entropy)
        self.register_handler("new_transaction", self.handle_new_transaction)    
        self.register_handler("broadcast_aggregate_entropy", self.handle_broadcast_aggregate_entropy)    
        if self.logger:
            self.logger.info(f"P2P Network initialized for node {node_id}")
        else:
            print(f"[DEBUG] Logger is None for P2P Network in node {self.node_id}")



    def test_logger(self):
        if self.logger:
            self.logger.info(f"Test log from P2P Network in node {self.node_id}")
        else:
            print(f"[DEBUG] Test logger is None for node {self.node_id}")

    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"[{self.node_id}] Listening on {self.host}:{self.port}...")

        # Start a thread to accept connections
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while True:
            conn, addr = self.socket.accept()
            print(f"[{self.node_id}] Connected to peer {addr}")
            threading.Thread(target=self.handle_peer, args=(conn,), daemon=True).start()

    def handle_peer(self, conn):
        while True:
            try:
                message = conn.recv(1024).decode("utf-8")
                if message:
                    self.process_message(message)
            except Exception as e:
                print(f"[{self.node_id}] Error handling peer: {e}")
                conn.close()
                break

    def connect_peer(self, host, port):
        self.peers.append((host, port))
        print(f"[{self.node_id}] Connected to peer {host}:{port}")

    def broadcast_entropy(self, aggregated_entropy):
        """
        Broadcast the aggregated entropy to all connected peers.
        :param aggregated_entropy: The aggregated entropy value to broadcast
        """
        
        self.logger.info(f"[{self.node_id}] Broadcasting aggregated entropy: {aggregated_entropy}")
        message_type = "broadcast_entropy"
        payload = {"aggregated_entropy": aggregated_entropy}

        # Pass the message type and payload to the generic broadcast_message function
        self.broadcast_message(message_type, payload)

    def broadcast_message(self, message_type, payload):
        """
        Broadcast a generic message to all connected peers.
        :param message_type: The type of message to broadcast.
        :param payload: The payload of the message.
        """
        self.logger.info(f"[{self.node_id}] Broadcasting message: {message_type} with payload: {payload}")

        for peer in self.peers:
            retries = 3
            while retries > 0:
                try:
                    # Map message_type to specific Flask endpoint
                    endpoint_map = {
                        "broadcast_aggregate_entropy": "receive_aggregate_entropy",
                    }
                    endpoint = endpoint_map.get(message_type, message_type)

                    response = requests.post(
                        f"{peer}/{endpoint}",
                        json=payload,
                        timeout=5  # Set timeout for safety
                    )
                    if response.status_code == 200:
                        self.logger.info(f"Message {message_type} broadcasted to {peer}. Response: {response.status_code}")
                        break  # Exit retry loop on success
                    else:
                        self.logger.error(f"Failed to broadcast {message_type} to {peer}: {response.status_code}. Retrying...")
                except requests.ConnectionError as e:
                    retries -= 1
                    self.logger.error(f"Connection error to {peer}. Retrying... ({3 - retries}/3)")
                    time.sleep(2)  # Wait before retrying
                except Exception as e:
                    self.logger.error(f"Failed to broadcast {message_type} to {peer}: {str(e)}")
                    break  # Exit loop on non-connection-related errors

    def register_handler(self, message_type, handler):
        self.handlers[message_type] = handler

    def process_message(self, message):
        try:
            message_data = json.loads(message)
            message_type = message_data.get("type")
            payload = message_data.get("payload")
            if message_type in self.handlers:
                self.handlers[message_type](payload)
            else:
                print(f"[{self.node_id}] No handler for message type: {message_type}")
        except Exception as e:
            print(f"[{self.node_id}] Failed to process message: {e}")

    def broadcast_transaction(self, transaction):
        """
        Broadcast a transaction to all connected peers.
        """
        if self.logger:
            self.logger.info(f"Broadcasting transaction: {transaction}")

        for peer in self.peers:
            retries = 3
            while retries > 0:
                try:
                    response = requests.post(
                        f"{peer}/add_transaction",
                        json={"transaction": transaction},
                        timeout=5  # Add timeout for safety
                    )
                    if self.logger:
                        self.logger.info(f"Transaction broadcasted to {peer}, Response: {response.status_code}")
                    break  # Exit retry loop on success
                except requests.exceptions.ConnectionError as e:
                    retries -= 1
                    self.logger.error(f"Failed to connect to {peer}. Retrying... ({3 - retries}/3)")
                    time.sleep(2)  # Wait before retrying
                except Exception as e:
                    self.logger.error(f"Failed to broadcast to {peer}: {str(e)}")
                    break  # Exit loop on non-connection-related errors

    def handle_broadcast_entropy(self, payload):
        try:
            data = json.loads(message)
            message_type = data.get("type")
            payload = data.get("payload")

            if message_type == "broadcast_entropy":
                aggregated_entropy = payload.get("aggregated_entropy")
                if aggregated_entropy is None:
                    self.logger.error("Received entropy is None. Check the broadcasting process.")
                else:
                    self.logger.info(f"Received broadcasted entropy: {aggregated_entropy}")
                    self.blockchain.received_entropy = aggregated_entropy
        except Exception as e:
            self.logger.error(f"Failed to handle message: {e}")

    # def broadcast_transaction(self, transaction):
    #     """
    #     Broadcast a transaction to all connected peers.
    #     """
    #     if self.logger:
    #         self.logger.info(f"Broadcasting transaction--: {transaction}")

    #     for peer in self.peers:
    #         try:
    #             response = requests.post(
    #                 f"{peer}/add_transaction",
    #                 json={"transaction": transaction},
    #             )
    #             if self.logger:
    #                 self.logger.info(f"Transaction broadcasted to {peer}, Response: {response.status_code}")
    #         except Exception as e:
    #             if self.logger:
    #                 self.logger.error(f"Failed to broadcast to {peer}: {str(e)}")


    
    def handle_new_transaction(self, payload):
        """
        Handle a transaction broadcast from another node.
        """
        if self.logger:
            self.logger.info(f"Handling new transaction payload: {payload}")

        transaction = payload.get("transaction")
        if transaction:
            self.logger.info(f"Processing received transaction: {transaction}")
            self.blockchain.add_transaction_to_pool(transaction)

        if self.logger:
            self.logger.info("Finished handling new transaction.")

    def broadcast_leader(self, leader_id):
        """
        Broadcast the leader ID to all peers.
        """
        if self.logger:
            self.logger.info(f"Broadcasting leader: {leader_id}")
        for peer in self.peers:
            while True:  # Retry indefinitely
                try:
                    response = requests.post(f"{peer}/set_leader", json={"leader_id": leader_id})
                    if response.status_code == 200:
                        self.logger.info(f"Leader broadcasted to {peer}, Response: {response.status_code}")
                        break  # Exit retry loop for this peer
                    else:
                        self.logger.error(f"Failed to broadcast leader to {peer}: {response.status_code}. Retrying...")
                except requests.ConnectionError as e:
                    self.logger.error(f"Failed to broadcast leader to {peer}: Connection error. Retrying...")
                except Exception as e:
                    self.logger.error(f"Failed to broadcast leader to {peer}: {str(e)}. Retrying...")

                time.sleep(5)  # Wait

    def broadcast_aggregate_entropy(self, aggregate_entropy, next_leader):
        """
        Broadcast the aggregate entropy and the next leader to all peers.
        """
        payload = {"aggregate_entropy": aggregate_entropy, "next_leader": next_leader}

        for peer in self.peers:
            while True:  # Retry until successful
                try:
                    response = requests.post(
                        f"{peer}/receive_aggregate_entropy", json=payload
                    )
                    if response.status_code == 200:
                        self.logger.info(f"Aggregate entropy broadcasted to {peer}")
                        break  # Exit retry loop on success
                    else:
                        self.logger.error(
                            f"Failed to broadcast aggregate entropy to {peer}: {response.status_code}. Retrying..."
                        )
                except requests.ConnectionError:
                    self.logger.error(f"Failed to connect to {peer}. Retrying...")
                except Exception as e:
                    self.logger.error(f"Error broadcasting aggregate entropy to {peer}: {str(e)}. Retrying...")
                time.sleep(5)  # Wait before retrying

    def handle_broadcast_aggregate_entropy(self, payload):
        """
        Handle broadcasted aggregate entropy and the next leader.
        """
        aggregate_entropy = payload.get("aggregate_entropy")
        next_leader = payload.get("next_leader")

        if aggregate_entropy is None or next_leader is None:
            self.logger.error("Invalid broadcast: missing aggregate entropy or next leader.")
            return

        # Update local values
        self.blockchain.aggregate_entropy = aggregate_entropy
        self.leader_id = next_leader
        self.is_leader = (self.node_id == next_leader)

        self.logger.info(f"Received broadcast: Aggregate entropy = {aggregate_entropy}, Next leader = {next_leader}")
