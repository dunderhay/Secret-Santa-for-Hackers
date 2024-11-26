import socket
import threading

class Socks5Proxy:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"SOCKS5 Proxy listening on {self.host}:{self.port}")

    def handle_client(self, client_socket):
        try:
            client_greeting = client_socket.recv(262)
            if client_greeting[0] != 0x05:
                print("Not a SOCKS5 client")
                client_socket.close()
                return

            client_socket.sendall(b"\x05\x00")
            
            request = client_socket.recv(4)
            mode = request[1]

            if mode != 0x01:
                print("Only CONNECT mode is supported.")
                client_socket.close()
                return

            address_type = request[3]
            if address_type == 0x01:
                address = socket.inet_ntoa(client_socket.recv(4))
            elif address_type == 0x03:
                domain_length = client_socket.recv(1)[0]
                address = client_socket.recv(domain_length).decode()
            else:
                print("Address type not supported.")
                client_socket.close()
                return
            port = int.from_bytes(client_socket.recv(2), 'big')
            
            print(f"Connecting to {address}:{port}")

            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((address, port))
            
            client_socket.sendall(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + (port).to_bytes(2, 'big'))
            
            self.relay_traffic(client_socket, remote_socket)
        
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def relay_traffic(self, client_socket, remote_socket):
        def forward(src, dst):
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
                print(f"Relayed data: {data.decode('utf-8', errors='replace')}")

        client_to_remote = threading.Thread(target=forward, args=(client_socket, remote_socket))
        remote_to_client = threading.Thread(target=forward, args=(remote_socket, client_socket))
        client_to_remote.start()
        remote_to_client.start()
        client_to_remote.join()
        remote_to_client.join()

    def start(self):
        print("Starting SOCKS5 proxy...")
        try:
            while True:
                client_socket, _ = self.server.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()
        except KeyboardInterrupt:
            print("Shutting down proxy.")
        finally:
            self.server.close()

if __name__ == "__main__":
    proxy = Socks5Proxy()
    proxy.start()
