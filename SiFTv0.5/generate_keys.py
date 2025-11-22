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

# Generate RSA key pair of specified size
def generate_rsa_keypair(key_size=2048):
    print(f"Generating {key_size}-bit RSA key pair...")
    key = RSA.generate(key_size)
    print("Key pair generated successfully!")
    return key

# Save the private key (full key pair) in PEM format
def save_private_key(key, filename='server_key.pem'):
    private_key_pem = key.export_key(format='PEM')
    
    with open(filename, 'wb') as f:
        f.write(private_key_pem)
    
    print(f"Private key saved to: {filename}")
    return filename

# Save the public key in PEM format
def save_public_key(key, filename='server_pubkey.pem'):
    public_key_pem = key.publickey().export_key(format='PEM')
    
    with open(filename, 'wb') as f:
        f.write(public_key_pem)
    
    print(f"Public key saved to: {filename}")
    return filename

# Main function
def main():
    print("=" * 60)
    print("SiFT v1.0 RSA Key Generation Utility")
    print("=" * 60)
    print()
    
    # Generate key pair
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
