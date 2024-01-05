import socket
import sys
from checksum import checksum

# Constants for local testing
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12000
FILENAME = "declaration.txt"  # Make sure this file exists in the same directory
TRANSMISSION_TIMEOUT = 3  # seconds

def create_packet(seq_num, data):
    """ Creates a packet with sequence number and data """
    data = data.ljust(20)  # Ensure data is 20 characters
    packet = f"{seq_num} 0 {data}"  # ACK number is not used in the sender's packet
    packet_checksum = checksum(packet)
    return f"{packet} {packet_checksum}"

def main():
    seq_num = 0

    # Establish a TCP connection
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    sock.settimeout(TRANSMISSION_TIMEOUT)

    try:
        with open(FILENAME, 'r') as file:
            data = file.read(200)

        for i in range(0, len(data), 20):
            packet_data = data[i:i+20]
            packet = create_packet(str(seq_num), packet_data)

            while True:
                try:
                    print(f"Sending packet: {packet}")  # Debugging print
                    sock.sendall(packet.encode())
                    ack = sock.recv(30).decode()
                    print(f"Received ACK: {ack}")  # Debugging print

                    ack_num = ack[2]
                    if ack_num == str(seq_num):
                        seq_num = 1 - seq_num
                        break
                except socket.timeout:
                    print("Timeout, resending packet.")  # Debugging print
                    continue

        print("Data sent successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()