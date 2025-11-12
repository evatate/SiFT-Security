from Crypto.PublicKey import RSA
from Crypto.Util.number import bytes_to_long, long_to_bytes
import base64

def generate_rsa_keys():
    # Generate 2048-bit RSA key pair
    key = RSA.generate(2048)
    
    # Private key in PEM format
    private_key = key.export_key()
    
    # Public key in PEM format  
    public_key = key.publickey().export_key()
    
    # Save private key for server
    with open('server_private.pem', 'wb') as f:
        f.write(private_key)
    
    # Save public key for client
    with open('client_public.pem', 'wb') as f:
        f.write(public_key)
    
    print("RSA keys generated successfully!")
    print("Private key saved as: server_private.pem")
    print("Public key saved as: client_public.pem")

if __name__ == '__main__':
    generate_rsa_keys()