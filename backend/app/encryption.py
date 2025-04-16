import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Load the encryption key from environment variables
# Generate a key using Fernet.generate_key() and store it securely
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY environment variable not set.")

# Ensure the key is bytes
ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()

# Create a Fernet instance with the key
f = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> bytes:
    """Encrypts string data."""
    if not data:
        return b'' # Return empty bytes if data is empty
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    """Decrypts byte data."""
    if not encrypted_data:
        return '' # Return empty string if data is empty
    return f.decrypt(encrypted_data).decode() 