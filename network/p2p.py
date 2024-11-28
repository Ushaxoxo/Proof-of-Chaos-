import json
import threading
import socket
from utils.logger import setup_logger

class P2PNetwork:
    
    def __init__(self, node_id, host="localhost", port=8000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = []  # List of connected peers (host, port)
        self.handlers = {}  # Message type -> handler function
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.register_handler("broadcast_entropy", self.handle_broadcast_entropy)
        self.logger = setup_logger(name=f"P2P_{self.node_id}", log_file=f"{self.node_id}_p2p.log", level="DEBUG")



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

    def broadcast_message(self, message_type, payload):
        """
        Broadcast a message to all connected peers.
        :param message_type: The type of message to broadcast (e.g., "broadcast_entropy").
        :param payload: The payload of the message (e.g., aggregated entropy).
        """
        message = json.dumps({"type": message_type, "payload": payload})
        self.logger.info(f"[{self.node_id}] Broadcasting message: {message}")

        for host, port in self.peers:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                    peer_socket.connect((host, port))
                    peer_socket.sendall(message.encode("utf-8"))
                    self.logger.info(f"[{self.node_id}] Sent message to {host}:{port}")
            except Exception as e:
                self.logger.error(f"[{self.node_id}] Failed to send message to {host}:{port}. Error: {e}")
    
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