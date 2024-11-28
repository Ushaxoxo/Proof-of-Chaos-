import hashlib
import random
import utils.logger 
# 1. Henon Map for Entropy Generation
def henon_entropy(a=1.4, b=0.3, iterations=10):
    x, y = random.random(), random.random()  # Start with random initial conditions
    for _ in range(iterations):
        x, y = 1 - a * x**2 + y, b * x
    return f"{x:.6f}_{y:.6f}"  # Return as a string for reproducibility

# 2. Deterministic Transaction Reordering
def reorder_transactions(transactions, entropy, logger=None):
   
    if entropy is None:
        raise ValueError("Entropy is None. Cannot reorder transactions without a valid entropy.")

    # Normalize the entropy to a consistent format
    entropy = f"{float(entropy):.6f}"

    # Calculate the deterministic seed
    seed = int(hashlib.sha256(entropy.encode()).hexdigest(), 16)

    # Log entropy and seed details
    # if logger:
    #     logger.debug(f"Entropy used for reordering: {entropy}")
    #     logger.debug(f"Deterministic seed generated: {seed}")
    
    # Initialize the random seed
    random.seed(seed)
    # if logger:
    #     logger.debug(f"Random seed initialized with value: {seed}")

    # Create a shuffled copy of the transactions
    shuffled_transactions = transactions[:]
    random.shuffle(shuffled_transactions)

    # Log before and after reordering
    # if logger:
    #     logger.debug(f"Original transactions: {transactions}")
    #     logger.debug(f"Shuffled transactions: {shuffled_transactions}")

    return shuffled_transactions

# 3. Weighted Average Fusion for Aggregating Entropies
def weighted_average_fusion(node_entropies, weights=None):
    total_weight = 0
    weighted_sum = 0

    if weights is None:
        weights = {node_id: 1 for node_id in node_entropies}  # Equal weights if none provided

    for node_id, entropy_str in node_entropies.items():
        if not isinstance(entropy_str, str):
            entropy_str = str(entropy_str)  # Ensure entropy is a string
        entropy_value = int(hashlib.sha256(entropy_str.encode()).hexdigest(), 16) % (2**32)
        weight = weights.get(node_id, 1)
        weighted_sum += entropy_value * weight
        total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 0

# 4. Weighted Minkowski Distance for Leader Selection
def weighted_minkowski_distance(node_entropy, aggregated_entropy, weights=None, p=2):
    distance = abs(node_entropy - aggregated_entropy)**p
    return distance

# 5. Entropy Validation
def validate_entropy(entropy):
    try:
        x, y = map(float, entropy.split("_"))
        return -1.5 <= x <= 1.5 and -0.5 <= y <= 0.5  # Henon bounds
    except (ValueError, AttributeError):
        return False

# 6. Utility to Convert Entropy to Numeric Value
def entropy_to_numeric(entropy):
    if entropy is None:
        raise ValueError("Entropy is None. Ensure all nodes have valid entropy values.")
    if not isinstance(entropy, str):  # Check if entropy is not a string
            entropy = str(entropy)  # Convert to string

    return int(hashlib.sha256(entropy.encode()).hexdigest(), 16) % (2**32)
