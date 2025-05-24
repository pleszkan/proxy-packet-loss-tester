import socket
import time
import random
import threading
import requests
import socks  # Add this import
from typing import Optional
from config import TestConfig, ProxyConfig, parse_client_args

class PacketClient:
    def __init__(self, config: TestConfig, proxy_config: Optional[ProxyConfig] = None):
        self.config = config
        self.proxy_config = proxy_config
        self.sock = None
        self.running = False
        self.sent_packets = 0
        self.received_acks = 0
        self.start_time = None
        self.last_stats_time = None
        self.stats_interval = 1.0  # Print stats every second
        self.sequence_number = 0
        self.lock = threading.Lock()  # For thread-safe stats updates

    def setup_socket(self):
        """Set up the socket based on protocol and proxy settings"""
        if self.proxy_config:
            if self.config.protocol == "tcp":
                # For TCP with proxy, use socks.socksocket
                self.verify_proxy()  # Verify proxy first
                self.sock = socks.socksocket()
                self.sock.set_proxy(
                    proxy_type=socks.SOCKS5,
                    addr=self.proxy_config.host,
                    port=self.proxy_config.port,
                    username=self.proxy_config.username,
                    password=self.proxy_config.password,
                    rdns=True
                )
                print(f"Socket configured to use SOCKS5 proxy: {self.proxy_config.host}:{self.proxy_config.port}")
            else:
                raise ValueError("SOCKS5 proxies only support TCP connections")
        else:
            # Direct connection
            if self.config.protocol == "tcp":
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:  # UDP
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.sock.settimeout(1.0)  # 1 second timeout for operations

    def verify_proxy(self):
        """Verify proxy connection by making a test request"""
        if not self.proxy_config:
            return

        proxies = {
            'http': f'socks5://{self.proxy_config.host}:{self.proxy_config.port}',
            'https': f'socks5://{self.proxy_config.host}:{self.proxy_config.port}'
        }

        if self.proxy_config.username and self.proxy_config.password:
            proxies['http'] = f'socks5://{self.proxy_config.username}:{self.proxy_config.password}@{self.proxy_config.host}:{self.proxy_config.port}'
            proxies['https'] = f'socks5://{self.proxy_config.username}:{self.proxy_config.password}@{self.proxy_config.host}:{self.proxy_config.port}'

        try:
            print("Verifying proxy connection...")
            print("Note: TCP connection will be verified, but UDP support is not guaranteed")
            response = requests.get('http://checkip.amazonaws.com', proxies=proxies, timeout=10)
            response.raise_for_status()
            print(f"Proxy connection successful! Current IP: {response.text.strip()}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect through proxy: {e}")

    def connect(self):
        """Connect to the server"""
        try:
            if self.proxy_config:
                if self.config.protocol == "tcp":
                    # For TCP with proxy, the proxy is already configured in the socket
                    self.sock.connect((self.config.host, self.config.port))
                    print(f"Connected to {self.config.host}:{self.config.port} through SOCKS5 proxy")
                else:
                    raise ValueError("SOCKS5 proxies only support TCP connections")
            else:
                if self.config.protocol == "tcp":
                    self.sock.connect((self.config.host, self.config.port))
                    print(f"Connected to {self.config.host}:{self.config.port}")
                # For UDP, no explicit connect needed
        except Exception as e:
            raise ConnectionError(f"Failed to connect to server: {e}")

    def send_packet(self):
        """Send a single packet and wait for acknowledgment"""
        try:
            # Generate random payload
            payload = random.randbytes(self.config.message_size)
            
            # Create packet with sequence number (8 bytes) + payload
            packet = self.sequence_number.to_bytes(8, byteorder='big') + payload
            
            if self.config.protocol == "tcp":
                self.sock.send(packet)
                try:
                    ack = self.sock.recv(8)  # Receive 8-byte acknowledgment
                    if len(ack) == 8:
                        ack_num = int.from_bytes(ack, byteorder='big')
                        if ack_num == self.sequence_number:
                            with self.lock:
                                self.received_acks += 1
                except socket.timeout:
                    pass  # No acknowledgment received
            else:  # UDP
                self.sock.sendto(packet, (self.config.host, self.config.port))
                try:
                    ack, _ = self.sock.recvfrom(8)  # Receive 8-byte acknowledgment
                    if len(ack) == 8:
                        ack_num = int.from_bytes(ack, byteorder='big')
                        if ack_num == self.sequence_number:
                            with self.lock:
                                self.received_acks += 1
                except socket.timeout:
                    pass  # No acknowledgment received
            
            with self.lock:
                self.sent_packets += 1
                self.sequence_number += 1
            
        except Exception as e:
            print(f"Error sending packet: {e}")
            raise

    def run(self):
        """Run the packet test"""
        try:
            self.setup_socket()
            self.connect()
            
            self.running = True
            self.start_time = time.time()
            self.last_stats_time = self.start_time
            
            print(f"Starting {self.config.protocol.upper()} test to {self.config.host}:{self.config.port}")
            if self.proxy_config:
                print(f"Using SOCKS5 proxy: {self.proxy_config.host}:{self.proxy_config.port}")
            print(f"Message size: {self.config.message_size} bytes")
            print(f"Test duration: {self.config.runtime} seconds")
            print("Press Ctrl+C to stop the test")
            
            end_time = self.start_time + self.config.runtime
            
            while self.running and time.time() < end_time:
                try:
                    self.send_packet()
                    
                    # Print periodic statistics
                    current_time = time.time()
                    if current_time - self.last_stats_time >= self.stats_interval:
                        self.print_current_stats()
                        self.last_stats_time = current_time
                    
                    # Small delay to prevent overwhelming the network
                    time.sleep(0.001)
                    
                except KeyboardInterrupt:
                    print("\nTest interrupted by user")
                    break
                except Exception as e:
                    print(f"Error during test: {e}")
                    break
            
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            self.cleanup()

    def stop(self):
        """Signal the client to stop"""
        self.running = False

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.sock:
                self.sock.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        self.print_final_stats()

    def print_current_stats(self):
        if not self.start_time:
            return
            
        duration = time.time() - self.start_time
        with self.lock:
            packets_per_second = self.sent_packets / duration if duration > 0 else 0
            ack_rate = (self.received_acks / self.sent_packets * 100) if self.sent_packets > 0 else 0
            
            print(f"\nCurrent Client Statistics:")
            print(f"Protocol: {self.config.protocol.upper()}")
            if self.proxy_config:
                print(f"Using SOCKS5 proxy: {self.proxy_config.host}:{self.proxy_config.port}")
            print(f"Packets sent: {self.sent_packets}")
            print(f"Packets acknowledged: {self.received_acks}")
            print(f"Acknowledgment rate: {ack_rate:.1f}%")
            print(f"Running time: {duration:.1f} seconds")
            print(f"Average packets per second: {packets_per_second:.1f}")

    def print_final_stats(self):
        if not self.start_time:
            return
            
        duration = time.time() - self.start_time
        with self.lock:
            packets_per_second = self.sent_packets / duration if duration > 0 else 0
            ack_rate = (self.received_acks / self.sent_packets * 100) if self.sent_packets > 0 else 0
            
            print(f"\nFinal Client Statistics:")
            print(f"Protocol: {self.config.protocol.upper()}")
            if self.proxy_config:
                print(f"Using SOCKS5 proxy: {self.proxy_config.host}:{self.proxy_config.port}")
            print(f"Total packets sent: {self.sent_packets}")
            print(f"Total packets acknowledged: {self.received_acks}")
            print(f"Final acknowledgment rate: {ack_rate:.1f}%")
            print(f"Total running time: {duration:.1f} seconds")
            print(f"Average packets per second: {packets_per_second:.1f}")

def main():
    config, proxy_config = parse_client_args()
    client = PacketClient(config, proxy_config)
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        client.stop()
        client.cleanup()

if __name__ == "__main__":
    main() 