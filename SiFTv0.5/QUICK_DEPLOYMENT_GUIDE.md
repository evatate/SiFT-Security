# Quick Deployment Guide for Your SiFT v0.5 → v1.0 Upgrade

## Your Current Structure

```
project/
├── server/
│   ├── server.py (v0.5)
│   ├── users.txt
│   ├── users/
│   │   ├── alice/
│   │   ├── bob/
│   │   └── charlie/
│   └── siftprotocols/
│       ├── __init__.py
│       ├── siftmtp.py (v0.5)
│       ├── siftlogin.py (v0.5)
│       ├── siftcmd.py (v0.5)
│       ├── siftupl.py (v0.5)
│       └── siftdnl.py (v0.5)
└── client/
    ├── client.py (v0.5)
    ├── test_1.txt
    ├── test_2.txt
    └── siftprotocols/
        ├── __init__.py
        ├── siftmtp.py (v0.5)
        ├── siftlogin.py (v0.5)
        ├── siftcmd.py (v0.5)
        ├── siftupl.py (v0.5)
        └── siftdnl.py (v0.5)
```

## Step-by-Step Deployment (15 minutes)

### Step 1: Generate RSA Keys (2 minutes)

In your project root directory:

```bash
# Download generate_keys.py from outputs
# Then run:
python3 generate_keys.py
```

This creates:
- `server_key.pem` (private key)
- `server_pubkey.pem` (public key)

### Step 2: Place Keys (1 minute)

```bash
# Copy private key to server
cp server_key.pem server/

# Copy public key to client
cp server_pubkey.pem client/
```

### Step 3: Backup Current Files (1 minute)

```bash
# Backup current versions (optional but recommended)
cp server/server.py server/server_v0.5_backup.py
cp server/siftprotocols/siftmtp.py server/siftprotocols/siftmtp_v0.5_backup.py
cp server/siftprotocols/siftlogin.py server/siftprotocols/siftlogin_v0.5_backup.py

cp client/client.py client/client_v0.5_backup.py
cp client/siftprotocols/siftmtp.py client/siftprotocols/siftmtp_v0.5_backup.py
cp client/siftprotocols/siftlogin.py client/siftprotocols/siftlogin_v0.5_backup.py
```

### Step 4: Update Server Files (3 minutes)

```bash
# Replace main server file
cp server_v1.py server/server.py

# Replace protocol files with v1.0 versions
cp siftmtp_v1.py server/siftprotocols/siftmtp.py
cp siftlogin_v1.py server/siftprotocols/siftlogin.py

# Keep these files unchanged:
# - siftcmd.py (no changes needed)
# - siftupl.py (no changes needed)
# - siftdnl.py (no changes needed)
# - __init__.py (no changes needed)
# - users.txt (no changes needed)
```

### Step 5: Update Client Files (3 minutes)

```bash
# Replace main client file
cp client_v1.py client/client.py

# Replace protocol files with v1.0 versions
cp siftmtp_v1.py client/siftprotocols/siftmtp.py
cp siftlogin_v1.py client/siftprotocols/siftlogin.py

# Keep these files unchanged:
# - siftcmd.py (no changes needed)
# - siftupl.py (no changes needed)
# - siftdnl.py (no changes needed)
# - __init__.py (no changes needed)
```

### Step 6: Verify File Structure (1 minute)

Your structure should now look like this:

```
project/
├── server/
│   ├── server.py (v1.0) ✓
│   ├── server_key.pem (NEW) ✓
│   ├── users.txt ✓
│   ├── users/
│   │   ├── alice/
│   │   ├── bob/
│   │   └── charlie/
│   └── siftprotocols/
│       ├── __init__.py ✓
│       ├── siftmtp.py (v1.0) ✓
│       ├── siftlogin.py (v1.0) ✓
│       ├── siftcmd.py ✓
│       ├── siftupl.py ✓
│       └── siftdnl.py ✓
└── client/
    ├── client.py (v1.0) ✓
    ├── server_pubkey.pem (NEW) ✓
    ├── test_1.txt ✓
    ├── test_2.txt ✓
    └── siftprotocols/
        ├── __init__.py ✓
        ├── siftmtp.py (v1.0) ✓
        ├── siftlogin.py (v1.0) ✓
        ├── siftcmd.py ✓
        ├── siftupl.py ✓
        └── siftdnl.py ✓
```

Check:
```bash
# Verify server has private key
ls -lh server/server_key.pem

# Verify client has public key
ls -lh client/server_pubkey.pem

# Should see both files with appropriate sizes
```

### Step 7: Test the System (5 minutes)

**Terminal 1 - Start Server:**
```bash
cd server
python3 server.py
```

Expected output:
```
======================================================================
SiFT v1.0 Server Started
======================================================================
Listening on 127.0.0.1:5150
Private key: server_key.pem
Press Ctrl-C to stop the server
======================================================================
```

**Terminal 2 - Start Client:**
```bash
cd client
python3 client.py
```

Expected output:
```
Connection to server established on 127.0.0.1:5150
Server public key loaded from server_pubkey.pem

   Username: 
```

**Login:**
```
Username: alice
Password: aaa
```

Expected output:
```
Login successful!

Client shell for the SiFT protocol. Type help or ? to list commands.

(sift)
```

**Test Commands:**
```
(sift) pwd
/
(sift) ls
[empty]
(sift) mkd testdir
(sift) ls
testdir/
(sift) upl test_1.txt
Starting upload...
...
Completed.
(sift) ls
testdir/
test_1.txt
(sift) bye
```

## What Changed?

### Files Replaced (3 files each side):
1. **server.py / client.py** - Added RSA key loading
2. **siftmtp.py** - Complete rewrite with encryption
3. **siftlogin.py** - Complete rewrite with key exchange

### Files Unchanged (4 files each side):
1. **siftcmd.py** - No changes (uses MTP transparently)
2. **siftupl.py** - No changes (uses MTP transparently)
3. **siftdnl.py** - No changes (uses MTP transparently)
4. **__init__.py** - No changes

### Files Added (1 file each side):
1. **server_key.pem** (server) - RSA private key
2. **server_pubkey.pem** (client) - RSA public key

## Troubleshooting

### Error: "Server private key file not found"
**Solution:**
```bash
# Make sure you ran generate_keys.py
python3 generate_keys.py

# Copy to server folder
cp server_key.pem server/
```

### Error: "Server public key file not found"
**Solution:**
```bash
# Copy to client folder
cp server_pubkey.pem client/
```

### Error: "Module 'Crypto' not found"
**Solution:**
```bash
pip3 install pycryptodome
```

### Error: "MAC verification failed"
**Solution:**
- Make sure both server and client have the updated v1.0 files
- Restart both server and client
- Regenerate keys if needed

### Error: "Sequence number mismatch"
**Solution:**
- Just logout and login again
- This resets sequence numbers

## Quick Test Script

Create `test_deployment.sh`:

```bash
#!/bin/bash
echo "Testing SiFT v1.0 deployment..."
echo ""

echo "1. Checking keys..."
if [ -f "server/server_key.pem" ]; then
    echo "   ✓ Server private key found"
else
    echo "   ✗ Server private key MISSING"
fi

if [ -f "client/server_pubkey.pem" ]; then
    echo "   ✓ Client public key found"
else
    echo "   ✗ Client public key MISSING"
fi

echo ""
echo "2. Checking server files..."
if grep -q "version_major = 1" server/siftprotocols/siftmtp.py; then
    echo "   ✓ Server MTP is v1.0"
else
    echo "   ✗ Server MTP is still v0.5"
fi

if grep -q "load_rsa_private_key" server/siftprotocols/siftlogin.py; then
    echo "   ✓ Server Login is v1.0"
else
    echo "   ✗ Server Login is still v0.5"
fi

echo ""
echo "3. Checking client files..."
if grep -q "version_major = 1" client/siftprotocols/siftmtp.py; then
    echo "   ✓ Client MTP is v1.0"
else
    echo "   ✗ Client MTP is still v0.5"
fi

if grep -q "load_rsa_public_key" client/siftprotocols/siftlogin.py; then
    echo "   ✓ Client Login is v1.0"
else
    echo "   ✗ Client Login is still v0.5"
fi

echo ""
echo "Deployment check complete!"
```

Run it:
```bash
chmod +x test_deployment.sh
./test_deployment.sh
```

## Summary of Commands

```bash
# 1. Generate keys
python3 generate_keys.py

# 2. Copy keys
cp server_key.pem server/
cp server_pubkey.pem client/

# 3. Update server
cp server_v1.py server/server.py
cp siftmtp_v1.py server/siftprotocols/siftmtp.py
cp siftlogin_v1.py server/siftprotocols/siftlogin.py

# 4. Update client
cp client_v1.py client/client.py
cp siftmtp_v1.py client/siftprotocols/siftmtp.py
cp siftlogin_v1.py client/siftprotocols/siftlogin.py

# 5. Test
cd server && python3 server.py
# In another terminal:
cd client && python3 client.py
```

## Your users.txt Is Already Compatible!

Your existing `users.txt` works perfectly with v1.0:
```
alice:b1f5edeaf196c54fab6df0759c4e8fff6f8db67bc29658f548fc5ff414211c8f:100000:49f28a513840295349a530b0e590f96d:alice/
bob:fc2a948f1dc717d4041474d82b55a2e01f5a3bf288afafe65937068b4a869e5a:100000:85c3743643452f410eee6e4129c9d3d5:bob/
charlie:d123b6125984eee899cb11362fe3c2964a29e433942b0766d3da2a898cccce87:100000:e6e0f19929edf9dcb055b4a978f95d79:charlie/
```

Format: `username:pwdhash:icount:salt:rootdir`

No changes needed to users.txt!

## Existing user folders work too!

Your `users/alice/`, `users/bob/`, and `users/charlie/` directories will continue to work. Any files already in these directories are accessible with v1.0.

## Done!

That's it! Your SiFT v0.5 is now upgraded to v1.0 with full cryptographic security.

Total time: ~15 minutes
Files changed: 6 (3 server + 3 client)
Files added: 2 (2 keys)
Files unchanged: 8 (4 server + 4 client)

Enjoy your secure file transfer system! 🔒
