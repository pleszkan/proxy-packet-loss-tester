import socket
import time
import select
import threading
from config import TestConfig, parse_server_args

class PacketServer:
    def __init__(self, config: TestConfig):
        self.config = config
        self.setup_socket()
        self.running = False
        self.received_packets = 0
        self.start_time = None
        self.last_stats_time = None
        self.stats_interval = 5.0  # Print stats every 5 seconds
        self.clients = set()  # For TCP connections

    def setup_socket(self):
        if self.config.protocol == "tcp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:  # UDP
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.sock.bind((self.config.host, self.config.port))
        if self.config.protocol == "tcp":
            self.sock.listen(5)
            self.sock.setblocking(False)
        else:
            self.sock.setblocking(False)

    def handle_tcp_client(self, client_sock, addr):
        """Handle individual TCP client connection"""
        try:
            while self.running:
                try:
                    data = client_sock.recv(self.config.message_size + 8)
                    if not data:
                        break
                    
                    # Extract sequence number (first 8 bytes) and payload
                    seq_num = int.from_bytes(data[:8], byteorder='big')
                    payload = data[8:]
                    
                    # Send acknowledgment with sequence number
                    ack = seq_num.to_bytes(8, byteorder='big')
                    client_sock.send(ack)
                    self.received_packets += 1
                    
                except socket.error as e:
                    if e.errno not in (socket.EAGAIN, socket.EWOULDBLOCK):
                        break
                    time.sleep(0.001)
        except Exception as e:
            print(f"Error handling TCP client {addr}: {e}")
        finally:
            client_sock.close()
            self.clients.remove(client_sock)

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.last_stats_time = self.start_time
        print(f"Server listening on {self.config.host}:{self.config.port} using {self.config.protocol.upper()}")
        print("Press Ctrl+C to stop the server")
        
        while self.running:
            try:
                if self.config.protocol == "tcp":
                    # Handle TCP connections
                    readable, _, _ = select.select([self.sock], [], [], 0.1)
                    if self.sock in readable:
                        try:
                            client_sock, addr = self.sock.accept()
                            client_sock.setblocking(False)
                            self.clients.add(client_sock)
                            client_thread = threading.Thread(
                                target=self.handle_tcp_client,
                                args=(client_sock, addr)
                            )
                            client_thread.daemon = True
                            client_thread.start()
                            print(f"New TCP client connected: {addr}")
                        except socket.error as e:
                            if e.errno not in (socket.EAGAIN, socket.EWOULDBLOCK):
                                raise
                else:
                    # Handle UDP packets
                    readable, _, _ = select.select([self.sock], [], [], 0.1)
                    if self.sock in readable:
                        try:
                            data, addr = self.sock.recvfrom(self.config.message_size + 8)
                            if not data:
                                continue
                            
                            # Extract sequence number (first 8 bytes) and payload
                            seq_num = int.from_bytes(data[:8], byteorder='big')
                            payload = data[8:]
                            
                            # Send acknowledgment with sequence number
                            ack = seq_num.to_bytes(8, byteorder='big')
                            self.sock.sendto(ack, addr)
                            self.received_packets += 1
                            
                        except socket.error as e:
                            if e.errno not in (socket.EAGAIN, socket.EWOULDBLOCK):
                                raise
                
                # Print periodic statistics
                current_time = time.time()
                if current_time - self.last_stats_time >= self.stats_interval:
                    self.print_current_stats()
                    self.last_stats_time = current_time
                
            except KeyboardInterrupt:
                print("\nShutdown signal received, stopping server...")
                break
            except Exception as e:
                print(f"Server error: {e}")
                break
        
        self.cleanup()

    def stop(self):
        """Signal the server to stop"""
        self.running = False

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.config.protocol == "tcp":
                # Close all client connections
                for client in self.clients:
                    try:
                        client.close()
                    except:
                        pass
                self.clients.clear()
            self.sock.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        self.print_final_stats()

    def print_current_stats(self):
        if not self.start_time:
            return
            
        duration = time.time() - self.start_time
        packets_per_second = self.received_packets / duration if duration > 0 else 0
        
        print(f"\nCurrent Server Statistics:")
        print(f"Protocol: {self.config.protocol.upper()}")
        if self.config.protocol == "tcp":
            print(f"Active clients: {len(self.clients)}")
        print(f"Total packets received: {self.received_packets}")
        print(f"Running time: {duration:.1f} seconds")
        print(f"Average packets per second: {packets_per_second:.1f}")

    def print_final_stats(self):
        if not self.start_time:
            return
            
        duration = time.time() - self.start_time
        packets_per_second = self.received_packets / duration if duration > 0 else 0
        
        print(f"\nFinal Server Statistics:")
        print(f"Protocol: {self.config.protocol.upper()}")
        if self.config.protocol == "tcp":
            print(f"Total clients handled: {len(self.clients)}")
        print(f"Total packets received: {self.received_packets}")
        print(f"Total running time: {duration:.1f} seconds")
        print(f"Average packets per second: {packets_per_second:.1f}")

def main():
    config = parse_server_args()
    server = PacketServer(config)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.stop()
        server.cleanup()

if __name__ == "__main__":
    main() 