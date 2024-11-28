import hashlib
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 1. Hashing Utilities
def sha256_hash(data):
    """
    Compute the SHA-256 hash of the given data.
    :param data: Input data as bytes or string
    :return: SHA-256 hash as a hex string
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

# 2. Key Management
def generate_rsa_keypair():
    """
    Generate an RSA public/private key pair.
    :return: (private_key, public_key)
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key

def serialize_private_key(private_key, password=None):
    """
    Serialize a private key with optional password encryption.
    :param private_key: RSA private key
    :param password: Password to encrypt the private key (optional)
    :return: Serialized private key as bytes
    """
    encryption_algorithm = (
        serialization.BestAvailableEncryption(password.encode("utf-8"))
        if password
        else serialization.NoEncryption()
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm,
    )

def serialize_public_key(public_key):
    """
    Serialize a public key.
    :param public_key: RSA public key
    :return: Serialized public key as bytes
    """
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

def load_private_key(serialized_key, password=None):
    """
    Load a private key from serialized bytes.
    :param serialized_key: Serialized private key bytes
    :param password: Password to decrypt the private key (optional)
    :return: RSA private key
    """
    return serialization.load_pem_private_key(
        serialized_key, password=password.encode("utf-8") if password else None
    )

def load_public_key(serialized_key):
    """
    Load a public key from serialized bytes.
    :param serialized_key: Serialized public key bytes
    :return: RSA public key
    """
    return serialization.load_pem_public_key(serialized_key)

# 3. Digital Signatures
def sign_data(private_key, data):
    """
    Sign data using a private key.
    :param private_key: RSA private key
    :param data: Data to sign as bytes or string
    :return: Digital signature
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

def verify_signature(public_key, data, signature):
    """
    Verify a digital signature.
    :param public_key: RSA public key
    :param data: Data that was signed
    :param signature: Digital signature to verify
    :return: True if the signature is valid, raises an exception otherwise
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    public_key.verify(
        signature,
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return True

# 4. Randomness
def generate_random_bytes(length=32):
    """
    Generate secure random bytes.
    :param length: Number of random bytes to generate
    :return: Random bytes
    """
    return os.urandom(length)
