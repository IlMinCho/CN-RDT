import socket
from checksum import checksum

# Constants
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12000

def create_ack_packet(ack_num):
    """ Creates an ACK packet with the given acknowledgment number """
    ack_packet = f"0 {ack_num} {' ' * 20}"  # Data field is blank in ACK packet
    ack_packet_checksum = checksum(ack_packet)
    return f"{ack_packet} {ack_packet_checksum}"

def main():
    expected_seq_num = 0

    # Create and bind the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.listen(1)

    print(f"Listening at {SERVER_IP}:{SERVER_PORT}")
    conn, addr = sock.accept()
    print(f"Connection from {addr}")

    received_data = ''
    try:
        while len(received_data) < 200:
            packet = conn.recv(30).decode()  # Specify buffer size explicitly

            if packet == '':
                print("Connection closed by sender.")
                break
            
            if len(packet) < 30:
                print("Incomplete packet received. Length:", len(packet))
                continue

            # Extract sequence number, payload, and checksum
            parts = packet.split(' ')
            seq_num = parts[0]
            payload = ' '.join(parts[2:-1])  # Join back the payload part
            packet_checksum = parts[-1]

            calculated_checksum = checksum(f"{seq_num} 0 {payload.ljust(20)}")

            print(seq_num)
            print(payload)
            print(packet_checksum)
            print(calculated_checksum)

            if calculated_checksum == packet_checksum and int(seq_num) == expected_seq_num:
                received_data += payload.strip()
                expected_seq_num = 1 - expected_seq_num

            ack_packet = create_ack_packet(seq_num)
            conn.sendall(ack_packet.encode())

        print("All data received successfully.")
        print("Received data:", received_data)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
        sock.close()

if __name__ == "__main__":
    main()