import hashlib
import time

class Block:
    def __init__(self, index, previous_hash, transactions, entropy, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.entropy = entropy
        self.timestamp = timestamp or time.time()
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_data = f"{self.index}{self.previous_hash}{self.transactions}{self.entropy}{self.timestamp}"
        return hashlib.sha256(block_data.encode()).hexdigest()

    def validate(self):
        return self.hash == self.compute_hash()

    def __repr__(self):
        return (
            f"Block(Index: {self.index}, "
            f"Hash: {self.hash}, "
            f"Previous Hash: {self.previous_hash}, "
            f"Transactions: {self.transactions}, "
            f"Entropy: {self.entropy}, "
            f"Timestamp: {self.timestamp})"
        )
