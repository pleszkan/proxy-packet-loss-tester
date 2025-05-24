# Proxy Tester

A network testing tool for measuring packet loss and network performance through SOCKS5 proxies. This tool allows you to test both TCP and UDP connections with configurable message sizes and test durations.

## Features

- Support for both TCP and UDP protocols
- SOCKS5 proxy support with optional authentication
- Configurable test parameters:
  - Message size
  - Number of messages or test duration
  - Connection timeout
  - Server host and port
- Packet loss measurement
- Network performance testing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pleszkan/proxy-packet-loss-tester.git
cd proxy-packet-loss-tester
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The tool consists of two components: a server and a client. You need to run the server first, then connect to it using the client.

### Server

The server component listens for incoming connections and measures packet statistics.

```bash
python server.py [options]
```

Options:
- `--host`: Server host to bind to (default: 0.0.0.0)
- `--port`: Server port (default: 5000)
- `--protocol`: Protocol to use - 'tcp' or 'udp' (default: udp)
- `--size`: Maximum message size in bytes (default: 1024)
- `--timeout`: Socket timeout in seconds (default: 1.0)

Example:
```bash
python server.py --host 0.0.0.0 --port 44444 --protocol tcp --size 1024
```

### Client

The client component connects to the server and sends test packets.

```bash
python client.py [options]
```

Required options:
- `--host`: Server host to connect to (required)
- Either `--messages` or `--runtime` must be specified

Additional options:
- `--port`: Server port (default: 5000)
- `--protocol`: Protocol to use - 'tcp' or 'udp' (default: udp)
- `--messages`: Number of messages to send
- `--runtime`: Test duration in seconds
- `--size`: Message size in bytes (default: 1024)
- `--timeout`: Socket timeout in seconds (default: 1.0)

SOCKS5 Proxy options:
- `--proxy-host`: SOCKS5 proxy host
- `--proxy-port`: SOCKS5 proxy port (required if proxy-host is specified)
- `--proxy-username`: SOCKS5 proxy username (if authentication required)
- `--proxy-password`: SOCKS5 proxy password (if authentication required)

Examples:

1. Basic test without proxy:
```bash
python client.py --host localhost --port 44444 --messages 1000 --size 1024 --protocol tcp
```

2. Test through SOCKS5 proxy:
```bash
python client.py --host localhost --port 44444 --runtime 60 --proxy-host proxy.example.com --proxy-port 1080 --protocol tcp
```

3. Test with authenticated proxy:
```bash
python client.py --host localhost --port 44444 --messages 1000 --proxy-host proxy.example.com --proxy-port 1080 --proxy-username user --proxy-password pass --protocol tcp
```

## Output

The tool will display statistics about the test, including:
- Number of packets sent/received
- Packet loss percentage
- Test duration
- Average round-trip time (if applicable)

## Requirements

- Python 3.6 or higher
- Dependencies listed in requirements.txt:
  - requests>=2.31.0
  - PySocks>=1.7.1
