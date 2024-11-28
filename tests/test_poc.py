import hashlib
import random
import copy
import json

def normalize_transactions(transactions):
    """Normalize transactions for consistency."""
    return [json.loads(json.dumps(tx, sort_keys=True)) for tx in transactions]

def reorder_transactions(transactions, entropy):
    """Reorder transactions deterministically based on entropy."""
    if entropy is None:
        raise ValueError("Entropy is None. Cannot reorder transactions without a valid entropy.")

    # Normalize entropy to 6 decimal places
    entropy = f"{float(entropy):.6f}"

    # Generate deterministic seed from entropy
    seed = int(hashlib.sha256(entropy.encode()).hexdigest(), 16)
    random.seed(seed)

    print(f"Entropy used: {entropy}")
    print(f"Generated seed: {seed}")

    # Deep copy transactions to avoid modifying the original
    shuffled_transactions = copy.deepcopy(transactions)
    print(f"Original transactions: {shuffled_transactions}")

    # Shuffle transactions deterministically
    random.shuffle(shuffled_transactions)
    print(f"Shuffled transactions: {shuffled_transactions}")

    return shuffled_transactions

def compare_transactions(list1, list2):
    """Compare two lists of transactions field by field."""
    for idx, (tx1, tx2) in enumerate(zip(list1, list2)):
        if tx1 != tx2:
            print(f"Transaction mismatch at index {idx}:")
            print(f"Proposer: {json.dumps(tx1, indent=2)}")
            print(f"Validator: {json.dumps(tx2, indent=2)}")
        else:
            print(f"Transaction at index {idx} matches.")

if __name__ == "__main__":
    proposer_transactions = [
        {"transaction_id": "aa87822462d1e52e0ee14352731dbf7e459d87ca05a18a62d353634e37b99938", 
         "sender": "Alice", 
         "receiver": "Bob", 
         "amount": 50, 
         "data": "", 
         "timestamp": 1732594647.500145},
        {"transaction_id": "e727eced56d9bf8945e1f15175235122f875e84e90b427caba6195d3002952c9", 
         "sender": "Charlie", 
         "receiver": "Dave", 
         "amount": 100, 
         "data": "", 
         "timestamp": 1732594647.500156},
        {"transaction_id": "8f4a8cfddd6cf63099dd530fe473bf690abf198e6821b8abd28289eab400bac5", 
         "sender": "Eve", 
         "receiver": "Frank", 
         "amount": 200, 
         "data": "", 
         "timestamp": 1732594647.50016},
    ]

    validation_transactions = [
        {"transaction_id": "e727eced56d9bf8945e1f15175235122f875e84e90b427caba6195d3002952c9", 
         "sender": "Charlie", 
         "receiver": "Dave", 
         "amount": 100, 
         "data": "", 
         "timestamp": 1732594647.500156},
        {"transaction_id": "8f4a8cfddd6cf63099dd530fe473bf690abf198e6821b8abd28289eab400bac5", 
         "sender": "Eve", 
         "receiver": "Frank", 
         "amount": 200, 
         "data": "", 
         "timestamp": 1732594647.50016},
        {"transaction_id": "aa87822462d1e52e0ee14352731dbf7e459d87ca05a18a62d353634e37b99938", 
         "sender": "Alice", 
         "receiver": "Bob", 
         "amount": 50, 
         "data": "", 
         "timestamp": 1732594647.500145},
    ]

    entropy = 3016671560.800000

    print("\n--- Normalizing Transactions ---")
    proposer_transactions = normalize_transactions(proposer_transactions)
    validation_transactions = normalize_transactions(validation_transactions)

    print("\nComparing Transactions Before Reordering:")
    compare_transactions(proposer_transactions, validation_transactions)

    print("\n--- Testing with Proposer Transactions ---")
    reordered_proposer = reorder_transactions(proposer_transactions, entropy)

    print("\n--- Testing with Validation Transactions ---")
    reordered_validation = reorder_transactions(validation_transactions, entropy)

    print("\n--- Comparing Reordered Lists ---")
    if reordered_proposer == reordered_validation:
        print("SUCCESS: Both reordered lists match.")
    else:
        print("FAILURE: Reordered lists do not match.")
