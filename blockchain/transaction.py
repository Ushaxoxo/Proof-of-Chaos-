import hashlib
import time

class Transaction:
    def __init__(self, sender, receiver, amount, data=None, timestamp=None):
   
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.data = data or ""
        self.timestamp = timestamp or time.time()
        self.transaction_id = self.compute_hash()

    def compute_hash(self):
      
        transaction_data = f"{self.sender}{self.receiver}{self.amount}{self.data}{self.timestamp}"
        return hashlib.sha256(transaction_data.encode()).hexdigest()

    def validate(self):
      
        if not self.sender or not self.receiver:
            return False
        if self.amount <= 0:
            return False
        return True

    def to_dict(self):
      
        return {
            "transaction_id": self.transaction_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
      
        return (
            f"Transaction(ID: {self.transaction_id}, "
            f"Sender: {self.sender}, Receiver: {self.receiver}, "
            f"Amount: {self.amount}, Data: {self.data}, Timestamp: {self.timestamp})"
        )
