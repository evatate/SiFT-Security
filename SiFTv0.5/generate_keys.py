#!/usr/bin/env python3
"""
RSA Key Generation Utility for SiFT v1.0
Generates a 2048-bit RSA key pair for the server.
- Private key (key pair) is saved in PEM format for the server
- Public key is exported in PEM format for the client
"""

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import sys

def generate_rsa_keypair(key_size=2048):
    """
    Generate an RSA key pair of specified size.
    
    Args:
        key_size: Size of the RSA key in bits (default: 2048)
    
    Returns:
        RSA key object containing both private and public keys
    """
    print(f"Generating {key_size}-bit RSA key pair...")
    key = RSA.generate(key_size)
    print("Key pair generated successfully!")
    return key

def save_private_key(key, filename='server_key.pem'):
    """
    Save the private key (full key pair) in PEM format.
    
    Args:
        key: RSA key object
        filename: Output filename for the private key
    """
    private_key_pem = key.export_key(format='PEM')
    
    with open(filename, 'wb') as f:
        f.write(private_key_pem)
    
    print(f"Private key saved to: {filename}")
    return filename

def save_public_key(key, filename='server_pubkey.pem'):
    """
    Export and save only the public key in PEM format.
    
    Args:
        key: RSA key object
        filename: Output filename for the public key
    """
    public_key_pem = key.publickey().export_key(format='PEM')
    
    with open(filename, 'wb') as f:
        f.write(public_key_pem)
    
    print(f"Public key saved to: {filename}")
    return filename

def main():
    """
    Main function to generate and save RSA key pair.
    """
    print("=" * 60)
    print("SiFT v1.0 RSA Key Generation Utility")
    print("=" * 60)
    print()
    
    # Generate the key pair
    key = generate_rsa_keypair(2048)
    
    print()
    print("Saving keys...")
    print("-" * 60)
    
    # Save private key for server
    private_key_file = save_private_key(key, 'server_key.pem')
    
    # Save public key for client
    public_key_file = save_public_key(key, 'server_pubkey.pem')
    
    print("-" * 60)
    print()
    print("Key generation complete!")
    print()
    print("IMPORTANT:")
    print(f"  1. Copy '{private_key_file}' to the SERVER folder")
    print(f"  2. Copy '{public_key_file}' to the CLIENT folder")
    print()
    print("The server will use the private key for decryption during login.")
    print("The client will use the public key to encrypt the temporary key.")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
