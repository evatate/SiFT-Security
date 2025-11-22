#python3

import os
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2, HKDF
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
from siftprotocols.siftmtp import SiFT_MTP, SiFT_MTP_Error


class SiFT_LOGIN_Error(Exception):

    def __init__(self, err_msg):
        self.err_msg = err_msg

class SiFT_LOGIN:
    def __init__(self, mtp):

        self.DEBUG = True
        # --------- CONSTANTS ------------
        self.delimiter = '\n'
        self.coding = 'utf-8'
        self.size_temp_key = 32  # 32-byte AES key
        self.size_random = 16    # 16-byte random value
        # --------- STATE ------------
        self.mtp = mtp
        self.server_users = None
        self.rsa_key = None  # RSA key (public for client, private for server)


    # Set RSA key
    def set_rsa_key(self, rsa_key):
        self.rsa_key = rsa_key


    # Load RSA public key from PEM file (for client)
    def load_rsa_public_key(self, pubkey_file):
        try:
            with open(pubkey_file, 'rb') as f:
                self.rsa_key = RSA.import_key(f.read())
            
            if self.rsa_key.has_private():
                raise SiFT_LOGIN_Error('Expected public key, but got private key')
                
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to load RSA public key --> {str(e)}')


    # Load RSA private key from PEM file (for server)
    def load_rsa_private_key(self, privkey_file):
        try:
            with open(privkey_file, 'rb') as f:
                self.rsa_key = RSA.import_key(f.read())
            
            if not self.rsa_key.has_private():
                raise SiFT_LOGIN_Error('Expected private key, but got public key')
                
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to load RSA private key --> {str(e)}')


    # Set user passwords dictionary (for server)
    def set_server_users(self, users):
        self.server_users = users


    # Build and parse login request
    def build_login_req(self, login_req_struct):
        login_req_str = login_req_struct['username']
        login_req_str += self.delimiter + login_req_struct['password']
        login_req_str += self.delimiter + login_req_struct['client_random'].hex()
        return login_req_str.encode(self.coding)


    # Parse login request
    def parse_login_req(self, login_req):
        login_req_fields = login_req.decode(self.coding).split(self.delimiter)
        login_req_struct = {}
        login_req_struct['username'] = login_req_fields[0]
        login_req_struct['password'] = login_req_fields[1]
        login_req_struct['client_random'] = bytes.fromhex(login_req_fields[2])
        return login_req_struct


    # Build and parse login response
    def build_login_res(self, login_res_struct):
        login_res_str = login_res_struct['request_hash'].hex()
        login_res_str += self.delimiter + login_res_struct['server_random'].hex()
        return login_res_str.encode(self.coding)


    # Parse login response
    def parse_login_res(self, login_res):
        login_res_fields = login_res.decode(self.coding).split(self.delimiter)
        login_res_struct = {}
        login_res_struct['request_hash'] = bytes.fromhex(login_res_fields[0])
        login_res_struct['server_random'] = bytes.fromhex(login_res_fields[1])
        return login_res_struct


    # Check password correctness
    def check_password(self, pwd, usr_struct):
        pwdhash = PBKDF2(pwd, usr_struct['salt'], len(usr_struct['pwdhash']), 
                        count=usr_struct['icount'], hmac_hash_module=SHA256)
        if pwdhash == usr_struct['pwdhash']: 
            return True
        return False


    # Derive session keys
    def derive_session_keys(self, client_random, server_random):
        # Master secret is concatenation of client and server randoms
        master_secret = client_random + server_random
        
        # Derive keys using HKDF-SHA256
        # No salt
        client_encrypt_key = HKDF(master_secret, 32, salt=None, 
                                  hashmod=SHA256, context=b'client_encryption_key')
        client_mac_key = HKDF(master_secret, 32, salt=None, 
                             hashmod=SHA256, context=b'client_MAC_key')
        server_encrypt_key = HKDF(master_secret, 32, salt=None, 
                                  hashmod=SHA256, context=b'server_encryption_key')
        server_mac_key = HKDF(master_secret, 32, salt=None, 
                             hashmod=SHA256, context=b'server_MAC_key')
        
        return client_encrypt_key, client_mac_key, server_encrypt_key, server_mac_key


    # Handle login on server side
    def handle_login_server(self):
        if not self.server_users:
            raise SiFT_LOGIN_Error('User database is required for handling login at server')

        if not self.rsa_key or not self.rsa_key.has_private():
            raise SiFT_LOGIN_Error('RSA private key required for server login')
        
        # Receive the header first
        try:
            msg_hdr = self.mtp.receive_bytes(self.mtp.size_msg_hdr)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to receive login request header --> ' + e.err_msg)

        # Parse header
        parsed_msg_hdr = self.mtp.parse_msg_header(msg_hdr)
        
        # Verify its a login request
        if parsed_msg_hdr['typ'] != self.mtp.type_login_req:
            raise SiFT_LOGIN_Error('Login request expected, but received something else')
        
        # Get message length
        msg_len = int.from_bytes(parsed_msg_hdr['len'], byteorder='big')
        
        # Calculate sizes
        body_len = msg_len - self.mtp.size_msg_hdr
        epd_len = body_len - self.mtp.size_msg_mac - self.mtp.size_etk
        
        # Receive encrypted payload
        try:
            encrypted_payload = self.mtp.receive_bytes(epd_len)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to receive encrypted payload --> ' + e.err_msg)
        
        # Receive MAC
        try:
            mac = self.mtp.receive_bytes(self.mtp.size_msg_mac)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to receive MAC --> ' + e.err_msg)
        
        # Receive encrypted temporary key
        try:
            etk = self.mtp.receive_bytes(self.mtp.size_etk)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to receive encrypted temporary key --> ' + e.err_msg)

        # Decrypt temporary key from etk using RSA-OAEP
        try:
            cipher = PKCS1_OAEP.new(self.rsa_key)
            temp_key = cipher.decrypt(etk)
            
            if len(temp_key) != self.size_temp_key:
                raise SiFT_LOGIN_Error('Decrypted temporary key has incorrect size')
            
            # Set temporary key in MTP (server side)
            self.mtp.set_temp_key(temp_key, is_client=False)
            
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to decrypt temporary key --> {str(e)}')
        
        # Decrypt the payload using the temporary key
        direction = self.mtp._get_direction(sending=False)
        
        try:
            msg_payload = self.mtp._decrypt_payload(
                encrypted_payload, mac, temp_key,
                parsed_msg_hdr['sqn'], parsed_msg_hdr['rnd'], 
                parsed_msg_hdr['rsv'], direction, msg_hdr
            )
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Failed to decrypt login request --> ' + e.err_msg)

        if self.DEBUG:
            print('Incoming login request payload (' + str(len(msg_payload)) + '):')
            print(msg_payload[:max(512, len(msg_payload))].decode('utf-8'))
            print('ETK (' + str(len(etk)) + '): ' + etk.hex()[:64] + '...')
            print('------------------------------------------')
        
        # Verify sequence number
        sqn_received = int.from_bytes(parsed_msg_hdr['sqn'], byteorder='big')
        if sqn_received != self.mtp.sqn_receive:
            raise SiFT_LOGIN_Error(f'Sequence number mismatch - expected {self.mtp.sqn_receive}, got {sqn_received}')
        
        # Increment receive sequence number
        self.mtp.sqn_receive += 1

        # Compute hash of login request payload
        hash_fn = SHA256.new()
        hash_fn.update(msg_payload)
        request_hash = hash_fn.digest()

        # Parse login request
        try:
            login_req_struct = self.parse_login_req(msg_payload)
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to parse login request --> {str(e)}')

        # Verify client_random size
        if len(login_req_struct['client_random']) != self.size_random:
            raise SiFT_LOGIN_Error('Client random has incorrect size')

        # Check username and password
        if login_req_struct['username'] in self.server_users:
            if not self.check_password(login_req_struct['password'], 
                                      self.server_users[login_req_struct['username']]):
                raise SiFT_LOGIN_Error('Password verification failed')
        else:
            raise SiFT_LOGIN_Error('Unknown user attempted to log in')

        # Generate server random
        server_random = get_random_bytes(self.size_random)

        # Build login response
        login_res_struct = {}
        login_res_struct['request_hash'] = request_hash
        login_res_struct['server_random'] = server_random
        msg_payload = self.build_login_res(login_res_struct)

        if self.DEBUG:
            print('Outgoing login response payload (' + str(len(msg_payload)) + '):')
            print(msg_payload[:max(512, len(msg_payload))].decode('utf-8'))
            print('------------------------------------------')

        # Derive session keys
        client_encrypt_key, client_mac_key, server_encrypt_key, server_mac_key = \
            self.derive_session_keys(login_req_struct['client_random'], server_random)

        if self.DEBUG:
            print('Derived session keys:')
            print(f'  client_encrypt_key: {client_encrypt_key.hex()}')
            print(f'  server_encrypt_key: {server_encrypt_key.hex()}')
            print('------------------------------------------')

        # Set session keys in MTP (server side, so is_client=False)
        self.mtp.set_session_keys(client_encrypt_key, server_encrypt_key, is_client=False)

        # Send login response
        try:
            self.mtp.send_msg(self.mtp.type_login_res, msg_payload)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to send login response --> ' + e.err_msg)

        # Reset sequence numbers for the actual session (after login exchange)
        self.mtp.sqn_send = 0
        self.mtp.sqn_receive = 0

        if self.DEBUG:
            print('User ' + login_req_struct['username'] + ' logged in')

        return login_req_struct['username']


    # Handle login on client side
    def handle_login_client(self, username, password):
        if not self.rsa_key or self.rsa_key.has_private():
            raise SiFT_LOGIN_Error('RSA public key required for client login')

        # Explicitly set is_client FIRST
        self.mtp.is_client = True

        # Generate temporary key
        temp_key = get_random_bytes(self.size_temp_key)
        
        # Set temporary key in MTP for this login request (client side)
        self.mtp.set_temp_key(temp_key, is_client=True)

        # Encrypt temporary key with server's RSA public key using RSA-OAEP
        try:
            cipher = PKCS1_OAEP.new(self.rsa_key)
            etk = cipher.encrypt(temp_key)
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to encrypt temporary key --> {str(e)}')

        # Generate client random
        client_random = get_random_bytes(self.size_random)

        # Build login request
        login_req_struct = {}
        login_req_struct['username'] = username
        login_req_struct['password'] = password
        login_req_struct['client_random'] = client_random
        msg_payload = self.build_login_req(login_req_struct)

        if self.DEBUG:
            print('Outgoing login request payload (' + str(len(msg_payload)) + '):')
            print(msg_payload[:max(512, len(msg_payload))].decode('utf-8'))
            print('ETK (' + str(len(etk)) + '): ' + etk.hex()[:64] + '...')
            print('------------------------------------------')

        # Compute hash of request payload
        hash_fn = SHA256.new()
        hash_fn.update(msg_payload)
        request_hash = hash_fn.digest()

        # Send login request (w/ encrypted temporary key)
        try:
            self.mtp.send_msg(self.mtp.type_login_req, msg_payload, etk=etk)
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to send login request --> ' + e.err_msg)

        # Try to receive a login response
        try:
            msg_type, msg_payload = self.mtp.receive_msg()
        except SiFT_MTP_Error as e:
            raise SiFT_LOGIN_Error('Unable to receive login response --> ' + e.err_msg)

        if self.DEBUG:
            print('Incoming login response payload (' + str(len(msg_payload)) + '):')
            print(msg_payload[:max(512, len(msg_payload))].decode('utf-8'))
            print('------------------------------------------')

        if msg_type != self.mtp.type_login_res:
            raise SiFT_LOGIN_Error('Login response expected, but received something else')

        # Parse login response
        try:
            login_res_struct = self.parse_login_res(msg_payload)
        except Exception as e:
            raise SiFT_LOGIN_Error(f'Failed to parse login response --> {str(e)}')

        # Verify request hash
        if login_res_struct['request_hash'] != request_hash:
            raise SiFT_LOGIN_Error('Verification of login response failed')

        # Verify server_random size
        if len(login_res_struct['server_random']) != self.size_random:
            raise SiFT_LOGIN_Error('Server random has incorrect size')

        # Derive session keys
        client_encrypt_key, client_mac_key, server_encrypt_key, server_mac_key = \
            self.derive_session_keys(client_random, login_res_struct['server_random'])

        if self.DEBUG:
            print('Derived session keys:')
            print(f'  client_encrypt_key: {client_encrypt_key.hex()}')
            print(f'  server_encrypt_key: {server_encrypt_key.hex()}')
            print('------------------------------------------')

        # Set session keys in MTP (client side, so is_client=True)
        self.mtp.set_session_keys(client_encrypt_key, server_encrypt_key, is_client=True)

        # Reset sequence numbers for the actual session (after login exchange)
        self.mtp.sqn_send = 0
        self.mtp.sqn_receive = 0

        if self.DEBUG:
            print('Login successful, session keys established')
