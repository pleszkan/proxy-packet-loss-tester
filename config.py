import argparse
from typing import Optional, Literal
from dataclasses import dataclass

@dataclass
class ProxyConfig:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class TestConfig:
    host: str = "localhost"
    port: int = 5000
    protocol: Literal["tcp", "udp"] = "udp"  # Default to UDP for backward compatibility
    num_messages: Optional[int] = None
    runtime: Optional[float] = None  # in seconds
    message_size: int = 1024  # bytes
    timeout: float = 1.0  # seconds
    proxy: Optional[ProxyConfig] = None

def parse_server_args():
    parser = argparse.ArgumentParser(description='Packet Loss Test Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--protocol', choices=['tcp', 'udp'], default='udp', help='Protocol to use (default: udp)')
    parser.add_argument('--size', type=int, default=1024, help='Maximum message size in bytes')
    parser.add_argument('--timeout', type=float, default=1.0, help='Socket timeout in seconds')
    
    args = parser.parse_args()
    return TestConfig(
        host=args.host,
        port=args.port,
        protocol=args.protocol,
        message_size=args.size,
        timeout=args.timeout
    )

def parse_client_args():
    parser = argparse.ArgumentParser(description='Packet Loss Test Client')
    parser.add_argument('--host', required=True, help='Server host to connect to')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--protocol', choices=['tcp', 'udp'], default='udp', help='Protocol to use (default: udp)')
    parser.add_argument('--messages', type=int, help='Number of messages to send')
    parser.add_argument('--runtime', type=float, help='Test duration in seconds')
    parser.add_argument('--size', type=int, default=1024, help='Message size in bytes')
    parser.add_argument('--timeout', type=float, default=1.0, help='Socket timeout in seconds')
    
    # Proxy configuration
    proxy_group = parser.add_argument_group('SOCKS5 Proxy Configuration')
    proxy_group.add_argument('--proxy-host', help='SOCKS5 proxy host')
    proxy_group.add_argument('--proxy-port', type=int, help='SOCKS5 proxy port')
    proxy_group.add_argument('--proxy-username', help='SOCKS5 proxy username (if authentication required)')
    proxy_group.add_argument('--proxy-password', help='SOCKS5 proxy password (if authentication required)')
    
    args = parser.parse_args()
    
    if not args.messages and not args.runtime:
        parser.error("Either --messages or --runtime must be specified")
    
    # Configure proxy if proxy host is provided
    proxy_config = None
    if args.proxy_host:
        if not args.proxy_port:
            parser.error("--proxy-port is required when using a proxy")
        proxy_config = ProxyConfig(
            host=args.proxy_host,
            port=args.proxy_port,
            username=args.proxy_username,
            password=args.proxy_password
        )
    
    test_config = TestConfig(
        host=args.host,
        port=args.port,
        protocol=args.protocol,
        num_messages=args.messages,
        runtime=args.runtime,
        message_size=args.size,
        timeout=args.timeout
    )
    
    return test_config, proxy_config 