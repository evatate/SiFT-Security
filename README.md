# SiFTv1.0 - Tara Salli and Eva Tate

## Overview

This project implements the SiFT v1.0 secure file transfer server and client, extending the provided v0.5 framework by completing the login protocol, message transfer protocol, directory and file operations, and key generation.

The following components were modified or added:

* **client.py** – updated to support the full login protocol, RSA-encrypted temporary key exchange, HKDF session key derivation, and MTP integration.
* **server.py** – updated to decrypt the temporary key, derive session keys, enforce sequence numbers, and correctly handle authentication, directories, upload/download, and file errors.
* **siftmtp.py** – added AES-GCM encryption/decryption, nonce construction, direction indicators, sequence number enforcement, temporary key use during login, and session key switching after login.
* **siftlogin.py** – updated to implement the complete key exchange (RSA-encrypted ETK, server decryption, HKDF derivation of client→server and server→client keys).
* **generate_keys.py** – new script to generate server_key.pem and server_pubkey.pem.

SiFTv1.0 now supports authenticated sessions, encrypted messaging, directory navigation, upload and download, and replay-protected sequence numbers.

---

## Setup: Key Generation

Run once from the root before first use:

```
python3 generate_keys.py
```

This creates:

* **server_key.pem** — server private key
* **server_pubkey.pem** — server public key

Next:

* Place **server_key.pem** in the **server** directory.
* Place **server_pubkey.pem** in the **client** directory.

The client uses the public key to encrypt the temporary AES key.
The server uses the private key to decrypt it.

---

## Next Step: Run the server and client

### Server

Start the server:

```
cd server
python3 server.py
```

The server listens for incoming client connections and handles login, commands, uploads, and downloads.

### Client

Start the client:

```
cd client
python3 client.py
```

This will result in:

```
Username:
Password:
```

After a successful login, you get the interactive shell:

```
(sift)
```

---

## Commands

```
pwd                 print current directory  
ls                  list files and directories  
cd <dir>            change directory  
mkd <dir>           create directory  
del <name>          delete file or empty directory  
upl <localfile>     upload file to server  
dnl <remotefile>    download file from server  
bye                 exit session  
```

---

## Basic Tests We Ran

1. Start in root:

```
(sift) pwd
/
(sift) ls
[empty]
```

2. Create and verify directory:

```
(sift) mkd testdir
(sift) ls
testdir/
```

3. Upload a file:

```
(sift) upl test_1.txt
Starting upload...
Completed.
```

4. Change directory:

```
(sift) cd testdir
(sift) pwd
/testdir/
```

5. Download a file:

```
(sift) cd ..
(sift) dnl test_1.txt
Completed.
```

6. Exit:

```
(sift) bye
```

---

## Notes on Functinoality

* Login messages use the temporary AES key established through RSA encryption.
* After login, all messages use AES-GCM with HKDF-derived session keys.
* MTP enforces sequence numbers for replay protection in both directions.
* User directories are stored under `users/<username>/`.