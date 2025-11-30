#python3

import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class SiFT_MTP_Error(Exception):

    def __init__(self, err_msg):
        self.err_msg = err_msg

class SiFT_MTP:
    def __init__(self, peer_socket):

        self.DEBUG = False  # Set to True only for development/debugging
        # --------- CONSTANTS ------------
        self.version_major = 1
        self.version_minor = 0
        self.msg_hdr_ver = b'\x01\x00'
        self.size_msg_hdr = 16
        self.size_msg_hdr_ver = 2
        self.size_msg_hdr_typ = 2
        self.size_msg_hdr_len = 2
        self.size_msg_hdr_sqn = 2
        self.size_msg_hdr_rnd = 6
        self.size_msg_hdr_rsv = 2
        self.size_msg_mac = 12
        self.size_nonce = 12  # sqn (2) + rnd (6) + rsv (2) + direction (2)
        self.size_etk = 256  # RSA-2048 encrypted key
        
        self.type_login_req =    b'\x00\x00'
        self.type_login_res =    b'\x00\x10'
        self.type_command_req =  b'\x01\x00'
        self.type_command_res =  b'\x01\x10'
        self.type_upload_req_0 = b'\x02\x00'
        self.type_upload_req_1 = b'\x02\x01'
        self.type_upload_res =   b'\x02\x10'
        self.type_dnload_req =   b'\x03\x00'
        self.type_dnload_res_0 = b'\x03\x10'
        self.type_dnload_res_1 = b'\x03\x11'
        self.msg_types = (self.type_login_req, self.type_login_res, 
                          self.type_command_req, self.type_command_res,
                          self.type_upload_req_0, self.type_upload_req_1, self.type_upload_res,
                          self.type_dnload_req, self.type_dnload_res_0, self.type_dnload_res_1)
        
        # Direction indicators for nonce construction
        self.dir_client_to_server = b'\x00\x00'
        self.dir_server_to_client = b'\x00\x01'
        
        # --------- STATE ------------
        self.peer_socket = peer_socket
        
        # Sequence numbers for replay protection
        self.sqn_send = 0
        self.sqn_receive = 0
        
        # Encryption keys (to be set by login protocol)
        self.client_encrypt_key = None
        self.server_encrypt_key = None
        
        # Temporary key (used only for login_req message)
        self.temp_key = None
        
        # Flag to indicate if we're client or server (for direction field)
        self.is_client = None  # Will be set when keys are established


    def set_temp_key(self, temp_key, is_client=True):
        """
        Set temporary key for login request encryption.
        
        Args:
            temp_key: 32-byte AES key for login_req message
            is_client: True if this is the client side (default: True)
        """
        if len(temp_key) != 32:
            raise SiFT_MTP_Error('Temporary key must be 32 bytes')
        self.temp_key = temp_key
        # Set is_client for direction determination
        if self.is_client is None:
            self.is_client = is_client


    def set_session_keys(self, client_encrypt_key, server_encrypt_key, is_client):
        """
        Set session keys derived from login protocol.
        
        Args:
            client_encrypt_key: 32-byte key for client->server messages
            server_encrypt_key: 32-byte key for server->client messages
            is_client: True if this is the client side, False if server side
        """
        if len(client_encrypt_key) != 32 or len(server_encrypt_key) != 32:
            raise SiFT_MTP_Error('Encryption keys must be 32 bytes each')
        
        self.client_encrypt_key = client_encrypt_key
        self.server_encrypt_key = server_encrypt_key
        self.is_client = is_client
        
        # Note: Sequence numbers will be reset after login exchange completes


    def _get_encryption_key(self, sending):
        """
        Get the appropriate encryption key based on direction.
        
        Args:
            sending: True if sending a message, False if receiving
        
        Returns:
            The appropriate encryption key
        """
        if self.is_client:
            return self.client_encrypt_key if sending else self.server_encrypt_key
        else:
            return self.server_encrypt_key if sending else self.client_encrypt_key


    def _get_direction(self, sending):
        """
        Get the direction indicator for nonce construction.
        
        Args:
            sending: True if sending a message, False if receiving
        
        Returns:
            Direction bytes for nonce
        
        Raises:
            SiFT_MTP_Error: If is_client is not set
        """
        if self.is_client is None:
            raise SiFT_MTP_Error('Direction cannot be determined - is_client not set')
        
        if self.is_client:
            return self.dir_client_to_server if sending else self.dir_server_to_client
        else:
            return self.dir_server_to_client if sending else self.dir_client_to_server


    def _build_nonce(self, sqn, rnd, rsv, direction):
        """
        Build 12-byte nonce for AES-GCM.
        
        Args:
            sqn: 2-byte sequence number
            rnd: 6-byte random value
            rsv: 2-byte reserved field
            direction: 2-byte direction indicator
        
        Returns:
            12-byte nonce
        """
        return sqn + rnd + rsv + direction


    def _encrypt_payload(self, payload, key, sqn, rnd, rsv, direction, header):
        """
        Encrypt payload using AES-GCM.
        
        Args:
            payload: Plaintext payload
            key: 32-byte encryption key
            sqn: 2-byte sequence number
            rnd: 6-byte random value
            rsv: 2-byte reserved field
            direction: 2-byte direction indicator
            header: 16-byte message header (used as additional authenticated data)
        
        Returns:
            Tuple of (encrypted_payload, mac_tag)
        """
        # Build nonce
        nonce = self._build_nonce(sqn, rnd, rsv, direction)
        
        # Create AES-GCM cipher
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=self.size_msg_mac)
        
        # Add header as additional authenticated data
        cipher.update(header)
        
        # Encrypt and get authentication tag
        encrypted_payload, mac_tag = cipher.encrypt_and_digest(payload)
        
        return encrypted_payload, mac_tag


    def _decrypt_payload(self, encrypted_payload, mac_tag, key, sqn, rnd, rsv, direction, header):
        """
        Decrypt payload using AES-GCM and verify MAC.
        
        Args:
            encrypted_payload: Ciphertext
            mac_tag: 12-byte authentication tag
            key: 32-byte encryption key
            sqn: 2-byte sequence number
            rnd: 6-byte random value
            rsv: 2-byte reserved field
            direction: 2-byte direction indicator
            header: 16-byte message header (used as additional authenticated data)
        
        Returns:
            Decrypted payload
        
        Raises:
            SiFT_MTP_Error: If MAC verification fails
        """
        # Build nonce
        nonce = self._build_nonce(sqn, rnd, rsv, direction)
        
        # Create AES-GCM cipher
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=self.size_msg_mac)
        
        # Add header as additional authenticated data
        cipher.update(header)
        
        # Decrypt and verify
        try:
            payload = cipher.decrypt_and_verify(encrypted_payload, mac_tag)
        except ValueError as e:
            raise SiFT_MTP_Error('MAC verification failed - message authentication error')
        
        return payload


    def parse_msg_header(self, msg_hdr):
        """
        Parse message header into dictionary.
        
        Args:
            msg_hdr: 16-byte header
        
        Returns:
            Dictionary with header fields
        """
        parsed_msg_hdr = {}
        i = 0
        
        parsed_msg_hdr['ver'] = msg_hdr[i:i+self.size_msg_hdr_ver]
        i += self.size_msg_hdr_ver
        
        parsed_msg_hdr['typ'] = msg_hdr[i:i+self.size_msg_hdr_typ]
        i += self.size_msg_hdr_typ
        
        parsed_msg_hdr['len'] = msg_hdr[i:i+self.size_msg_hdr_len]
        i += self.size_msg_hdr_len
        
        parsed_msg_hdr['sqn'] = msg_hdr[i:i+self.size_msg_hdr_sqn]
        i += self.size_msg_hdr_sqn
        
        parsed_msg_hdr['rnd'] = msg_hdr[i:i+self.size_msg_hdr_rnd]
        i += self.size_msg_hdr_rnd
        
        parsed_msg_hdr['rsv'] = msg_hdr[i:i+self.size_msg_hdr_rsv]
        
        return parsed_msg_hdr


    def receive_bytes(self, n):
        """
        Receive exactly n bytes from peer socket.
        
        Args:
            n: Number of bytes to receive
        
        Returns:
            Received bytes
        
        Raises:
            SiFT_MTP_Error: If connection breaks or cannot receive
        """
        bytes_received = b''
        bytes_count = 0
        while bytes_count < n:
            try:
                chunk = self.peer_socket.recv(n-bytes_count)
            except:
                raise SiFT_MTP_Error('Unable to receive via peer socket')
            if not chunk: 
                raise SiFT_MTP_Error('Connection with peer is broken')
            bytes_received += chunk
            bytes_count += len(chunk)
        return bytes_received


    def receive_msg(self):
        """
        Receive and decrypt a message.
        
        Returns:
            Tuple of (msg_type, msg_payload)
        
        Raises:
            SiFT_MTP_Error: On any receive or decryption error
        """
        # Receive header
        try:
            msg_hdr = self.receive_bytes(self.size_msg_hdr)
        except SiFT_MTP_Error as e:
            raise SiFT_MTP_Error('Unable to receive message header --> ' + e.err_msg)

        if len(msg_hdr) != self.size_msg_hdr: 
            raise SiFT_MTP_Error('Incomplete message header received')
        
        # Parse header
        parsed_msg_hdr = self.parse_msg_header(msg_hdr)

        # Verify version
        if parsed_msg_hdr['ver'] != self.msg_hdr_ver:
            raise SiFT_MTP_Error('Unsupported version found in message header')

        # Verify message type
        if parsed_msg_hdr['typ'] not in self.msg_types:
            raise SiFT_MTP_Error('Unknown message type found in message header')

        # Get message length
        msg_len = int.from_bytes(parsed_msg_hdr['len'], byteorder='big')
        
        # Calculate payload and MAC size (no etk handling here - login protocol does it manually)
        body_len = msg_len - self.size_msg_hdr
        epd_len = body_len - self.size_msg_mac

        # Receive encrypted payload
        try:
            encrypted_payload = self.receive_bytes(epd_len)
        except SiFT_MTP_Error as e:
            raise SiFT_MTP_Error('Unable to receive encrypted payload --> ' + e.err_msg)

        # Receive MAC
        try:
            mac = self.receive_bytes(self.size_msg_mac)
        except SiFT_MTP_Error as e:
            raise SiFT_MTP_Error('Unable to receive MAC --> ' + e.err_msg)

        # DEBUG 
        if self.DEBUG:
            print('MTP message received (' + str(msg_len) + '):')
            print('HDR (' + str(len(msg_hdr)) + '): ' + msg_hdr.hex())
            print('EPD (' + str(len(encrypted_payload)) + '): ' + encrypted_payload.hex())
            print('MAC (' + str(len(mac)) + '): ' + mac.hex())
            print('------------------------------------------')
        # DEBUG 

        # Verify sequence number
        sqn_received = int.from_bytes(parsed_msg_hdr['sqn'], byteorder='big')
        if sqn_received != self.sqn_receive:
            raise SiFT_MTP_Error(f'Sequence number mismatch - expected {self.sqn_receive}, got {sqn_received}')

        # Determine which key to use (temp_key for login_res, session keys for everything else)
        if parsed_msg_hdr['typ'] == self.type_login_res:
            # Login response uses temporary key
            if self.temp_key is None:
                raise SiFT_MTP_Error('Temporary key not set for login response')
            key = self.temp_key
        else:
            # Other messages use session keys
            key = self._get_encryption_key(sending=False)
            if key is None:
                raise SiFT_MTP_Error('Session keys not set')

        # Get direction for nonce
        direction = self._get_direction(sending=False)

        # Decrypt payload
        try:
            msg_payload = self._decrypt_payload(
                encrypted_payload, mac, key,
                parsed_msg_hdr['sqn'], parsed_msg_hdr['rnd'], 
                parsed_msg_hdr['rsv'], direction, msg_hdr
            )
        except SiFT_MTP_Error as e:
            raise SiFT_MTP_Error('Decryption failed --> ' + e.err_msg)

        # Increment receive sequence number
        self.sqn_receive += 1

        return parsed_msg_hdr['typ'], msg_payload


    def send_bytes(self, bytes_to_send):
        """
        Send all bytes via peer socket.
        
        Args:
            bytes_to_send: Bytes to send
        
        Raises:
            SiFT_MTP_Error: If unable to send
        """
        try:
            self.peer_socket.sendall(bytes_to_send)
        except:
            raise SiFT_MTP_Error('Unable to send via peer socket')


    def send_msg(self, msg_type, msg_payload, etk=None):
        """
        Encrypt and send a message.
        
        Args:
            msg_type: 2-byte message type
            msg_payload: Plaintext payload
            etk: Encrypted temporary key (256 bytes, only for login_req)
        
        Raises:
            SiFT_MTP_Error: On any send or encryption error
        """
        # Generate random field
        rnd = get_random_bytes(self.size_msg_hdr_rnd)
        
        # Reserved field (always zeros)
        rsv = b'\x00\x00'
        
        # Sequence number
        sqn = self.sqn_send.to_bytes(self.size_msg_hdr_sqn, byteorder='big')
        
        # Determine which key to use
        if msg_type == self.type_login_req or msg_type == self.type_login_res:
            # Login request and response use temporary key
            if self.temp_key is None:
                raise SiFT_MTP_Error('Temporary key not set for login message')
            key = self.temp_key
            if msg_type == self.type_login_req:
                if etk is None or len(etk) != self.size_etk:
                    raise SiFT_MTP_Error('Encrypted temporary key required for login request')
        else:
            # Other messages use session keys
            key = self._get_encryption_key(sending=True)
            if key is None:
                raise SiFT_MTP_Error('Session keys not set')
        
        # Get direction for nonce
        direction = self._get_direction(sending=True)
        
        # Build header (without length first)
        msg_hdr_without_len = self.msg_hdr_ver + msg_type
        
        # Calculate message length
        if msg_type == self.type_login_req:
            msg_len = self.size_msg_hdr + len(msg_payload) + self.size_msg_mac + self.size_etk
        else:
            msg_len = self.size_msg_hdr + len(msg_payload) + self.size_msg_mac
        
        msg_hdr_len = msg_len.to_bytes(self.size_msg_hdr_len, byteorder='big')
        
        # Complete header
        msg_hdr = msg_hdr_without_len + msg_hdr_len + sqn + rnd + rsv
        
        # Encrypt payload
        try:
            encrypted_payload, mac = self._encrypt_payload(
                msg_payload, key, sqn, rnd, rsv, direction, msg_hdr
            )
        except Exception as e:
            raise SiFT_MTP_Error('Encryption failed --> ' + str(e))

        # Build complete message
        if msg_type == self.type_login_req:
            msg = msg_hdr + encrypted_payload + mac + etk
        else:
            msg = msg_hdr + encrypted_payload + mac

        # DEBUG 
        if self.DEBUG:
            print('MTP message to send (' + str(msg_len) + '):')
            print('HDR (' + str(len(msg_hdr)) + '): ' + msg_hdr.hex())
            print('EPD (' + str(len(encrypted_payload)) + '): ' + encrypted_payload.hex())
            print('MAC (' + str(len(mac)) + '): ' + mac.hex())
            if etk:
                print('ETK (' + str(len(etk)) + '): ' + etk.hex())
            print('------------------------------------------')
        # DEBUG 

        # Send message
        try:
            self.send_bytes(msg)
        except SiFT_MTP_Error as e:
            raise SiFT_MTP_Error('Unable to send message to peer --> ' + e.err_msg)
        
        # Increment send sequence number
        self.sqn_send += 1