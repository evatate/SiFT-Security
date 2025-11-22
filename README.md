# SiFT v1.0 - Simple File Transfer Protocol with Cryptographic Security

**Authors:** Eva Tate (@evatate) and Tara Salli (@taramsalli)
**Version:** 1.0  
**Date:** December 2025  

## Overview

SiFT v1.0 is a secure file transfer protocol that adds end-to-end encryption, mutual authentication, and replay protection to the baseline v0.5 protocol.

### Key Features

- **AES-256-GCM** encryption for all messages
- **RSA-2048** key exchange with HKDF key derivation
- **Replay protection** via sequence numbers
- **Mutual authentication** (RSA + password)
- **7 file commands:** pwd, ls, cd, mkd, del, upl, dnl

### Security Primitives

| Primitive | Purpose |
|-----------|---------|
| RSA-2048 (OAEP) | Key exchange |
| AES-256-GCM | Encryption & authentication |
| HKDF-SHA256 | Key derivation (4 × 32-byte keys) |
| PBKDF2-SHA256 | Password hashing (100k iterations) |

## Protocol Design

### Message Format (16-byte header + encrypted payload + 12-byte MAC)

Header: ver(2) | typ(2) | len(2) | sqn(2) | rnd(6) | rsv(2)

### Key Exchange Flow

1. Client generates 32-byte temp_key and 16-byte client_random
2. Client encrypts temp_key with server's RSA public key → login_req
3. Server decrypts temp_key, generates 16-byte server_random → login_res
4. Both derive session keys: `HKDF(client_random || server_random)`

## Implementation

### Directory Structure
```
server/
├── server.py, server_key.pem, users.txt
└── siftprotocols/ (6 modules)

client/
├── client.py, server_pubkey.pem, test files
└── siftprotocols/ (6 modules)
```

## Installation

**Prerequisites:** Python 3.6+, PyCryptodome

```bash
pip3 install pycryptodome
```

**Setup:**
```bash
# 1. Generate keys
python3 generate_keys.py

# 2. Deploy keys
cp server_key.pem server/
cp server_pubkey.pem client/

# 3. Start server
cd server && python3 server.py

# 4. Start client (new terminal)
cd client && python3 client.py

# 5. Login (test accounts)
# alice/aaa, bob/bbb, or charlie/ccc
```

## Testing

Run unit tests for crypto components:
```bash
python3 -c "from Crypto.Cipher import AES; from Crypto.Random import get_random_bytes; cipher = AES.new(get_random_bytes(32), AES.MODE_GCM, nonce=get_random_bytes(12)); print('✓ AES-GCM')"
```

## Security Analysis

**Protects against:** Eavesdropping, tampering, replay attacks, MITM, impersonation

**Limitations:** No perfect forward secrecy, no DoS protection, no rate limiting

**Best practices:** Secure server_key.pem (chmod 600), use strong passwords, monitor logs

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module 'Crypto' not found | `pip3 install pycryptodome` |
| Server key not found | Run `generate_keys.py` and copy to server/ |
| MAC verification failed | Restart both, ensure both have v1.0 files |
| Sequence mismatch | Logout and login to reset |

**Debug mode:** Set `self.DEBUG = True` in siftmtp.py and siftlogin.py

## Documentation

See `/docs` for complete documentation:
- `QUICK_DEPLOYMENT_GUIDE.md` - Step-by-step deployment
- `IMPLEMENTATION_PLAN.md` - Technical specifications  

## Authors

**Eva Tate and Tara Salli**  
AIT Budapest - Cryptography Course Final Project - Fall 2025
