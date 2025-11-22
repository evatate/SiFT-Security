#python3

import sys, threading, socket, getpass, os
from siftprotocols.siftmtp import SiFT_MTP, SiFT_MTP_Error
from siftprotocols.siftlogin import SiFT_LOGIN, SiFT_LOGIN_Error
from siftprotocols.siftcmd import SiFT_CMD, SiFT_CMD_Error

class Server:
    def __init__(self):
        # ------------------------ CONFIG -----------------------------
        self.server_usersfile = 'users.txt' 
        self.server_usersfile_coding = 'utf-8'
        self.server_usersfile_rec_delimiter = '\n'
        self.server_usersfile_fld_delimiter = ':'
        self.server_rootdir = './users/'
        self.server_privkeyfile = 'server_key.pem'  # RSA private key file
        self.server_ip = socket.gethostbyname('localhost')
        # self.server_ip = socket.gethostbyname(socket.gethostname())
        self.server_port = 5150
        # -------------------------------------------------------------
        
        # Check if private key file exists
        if not os.path.exists(self.server_privkeyfile):
            print('=' * 70)
            print('ERROR: Server private key file not found!')
            print('=' * 70)
            print(f'Cannot find: {self.server_privkeyfile}')
            print()
            print('Please generate the RSA key pair first:')
            print('  1. Run: python3 generate_keys.py')
            print('  2. Copy server_key.pem to the server folder')
            print('=' * 70)
            sys.exit(1)
        
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.listen(5)
        
        print('=' * 70)
        print('SiFT v1.0 Server Started')
        print('=' * 70)
        print(f'Listening on {self.server_ip}:{self.server_port}')
        print(f'Private key: {self.server_privkeyfile}')
        print('Press Ctrl-C to stop the server')
        print('=' * 70)
        
        self.accept_connections()


    def load_users(self, usersfile):
        users = {}
        with open(usersfile, 'rb') as f:
            allrecords = f.read().decode(self.server_usersfile_coding)
        records = allrecords.split(self.server_usersfile_rec_delimiter)
        for r in records:
            if not r.strip(): # skip empty lines
                continue
            fields = r.split(self.server_usersfile_fld_delimiter)
            username = fields[0]
            usr_struct = {}
            usr_struct['pwdhash'] = bytes.fromhex(fields[1])
            usr_struct['icount'] = int(fields[2])
            usr_struct['salt'] = bytes.fromhex(fields[3])
            usr_struct['rootdir'] = fields[4]
            users[username] = usr_struct
        return users


    def accept_connections(self):
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr, )).start()
        except KeyboardInterrupt:
            print('\n' + '=' * 70)
            print('Server shutdown requested')
            print('=' * 70)
            self.server_socket.close()
            sys.exit(0)


    def handle_client(self, client_socket, addr):
        print('New client on ' + addr[0] + ':' + str(addr[1]))

        mtp = SiFT_MTP(client_socket)

        loginp = SiFT_LOGIN(mtp)
        
        # Load servers RSA private key
        try:
            loginp.load_rsa_private_key(self.server_privkeyfile)
        except SiFT_LOGIN_Error as e:
            print('SiFT_LOGIN_Error: Failed to load private key --> ' + e.err_msg)
            print('Closing connection with client on ' + addr[0] + ':' + str(addr[1]))
            client_socket.close()
            return
        
        # Load users database
        users = self.load_users(self.server_usersfile)
        loginp.set_server_users(users)

        # Handle login
        try:
            user = loginp.handle_login_server()
        except SiFT_LOGIN_Error as e:
            print('SiFT_LOGIN_Error: ' + e.err_msg)
            print('Closing connection with client on ' + addr[0] + ':' + str(addr[1]))
            client_socket.close()
            return

        # Setup command protocol
        cmdp = SiFT_CMD(mtp)
        cmdp.set_server_rootdir(self.server_rootdir)
        cmdp.set_user_rootdir(users[user]['rootdir'])

        # Handle commands
        while True:
            try:
                cmdp.receive_command()
            except SiFT_CMD_Error as e:
                print('SiFT_CMD_Error: ' + e.err_msg)
                print('Closing connection with client on ' + addr[0] + ':' + str(addr[1]))
                client_socket.close()
                return
            except SiFT_MTP_Error as e:
                print('SiFT_MTP_Error: ' + e.err_msg)
                print('Closing connection with client on ' + addr[0] + ':' + str(addr[1]))
                client_socket.close()
                return


# main
if __name__ == '__main__':
    server = Server()
