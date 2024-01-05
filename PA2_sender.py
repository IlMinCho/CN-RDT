#!/usr/bin/env python3
# Last updated: Oct, 2021

import sys
import socket
import datetime
from checksum import checksum, checksum_verifier

CONNECTION_TIMEOUT = 60 # timeout when the sender cannot find the receiver within 60 seconds
FIRST_NAME = "Ilmin"
LAST_NAME = "Cho"

def establish_connection(server_ip, server_port, connection_ID, role, loss_rate, corrupt_rate, max_delay):
    """ Establish a connection to the gaia.cs.umass.edu server """
    try:
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the server
        sock.connect((server_ip, server_port))

        # Send "HELLO" message
        hello_message = f"HELLO {role} {loss_rate} {corrupt_rate} {max_delay} {connection_ID}"
        sock.sendall(hello_message.encode())

        # Receive response
        while True:
            response = sock.recv(1024).decode()
            if 'OK' in response:
                print("Connection Established with ID:", connection_ID)
                return sock
            elif 'WAITING' in response:
                print("Waiting for the other client to connect.")
                continue  # Stay in the loop and wait for OK or ERROR
            elif 'ERROR' in response:
                print("Error received from server:", response)
                sock.close()
                return None
            else:
                print("Unexpected response:", response)
                sock.close()
                return None

    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return None
    except KeyboardInterrupt:
        sock.close()
        return None
    
def create_packet(seq_num, data):
    """ Creates a packet with a sequence number and data """
    data = data.ljust(20)  # Ensure data is exactly 20 bytes
    packet = f"{seq_num} 0 {data} "  # ACK num is not used in sender packet
    packet_checksum = checksum(packet)  # Calculate checksum
    return f"{packet}{packet_checksum}"


def start_sender(server_ip, server_port, connection_ID, loss_rate=0, corrupt_rate=0, max_delay=0, transmission_timeout=60, filename="declaration.txt"):
    """
     This function runs the sender, connnect to the server, and send a file to the receiver.
     The function will print the checksum, number of packet sent/recv/corrupt recv/timeout at the end. 
     The checksum is expected to be the same as the checksum that the receiver prints at the end.

     Input: 
        server_ip - IP of the server (String)
        server_port - Port to connect on the server (int)
        connection_ID - your sender and receiver should specify the same connection ID (String)
        loss_rate - the probabilities that a message will be lost (float - default is 0, the value should be between 0 to 1)
        corrupt_rate - the probabilities that a message will be corrupted (float - default is 0, the value should be between 0 to 1)
        max_delay - maximum delay for your packet at the server (int - default is 0, the value should be between 0 to 5)
        tranmission_timeout - waiting time until the sender resends the packet again (int - default is 60 seconds and cannot be 0)
        filename - the path + filename to send (String)

     Output: 
        checksum_val - the checksum value of the file sent (String that always has 5 digits)
        total_packet_sent - the total number of packet sent (int)
        total_packet_recv - the total number of packet received, including corrupted (int)
        total_corrupted_pkt_recv - the total number of corrupted packet receieved (int)
        total_timeout - the total number of timeout (int)

    """

    print("Student name: {} {}".format(FIRST_NAME, LAST_NAME))
    print("Start running sender: {}".format(datetime.datetime.now()))

    checksum_val = "00000"
    total_packet_sent = 0
    total_packet_recv = 0
    total_corrupted_pkt_recv = 0
    total_timeout =  0

    print("Connecting to server: {}, {}, {}".format(server_ip, server_port, connection_ID))

    ##### START YOUR IMPLEMENTATION HERE #####
    loss_rate = 0.0 if not (0.0 <= float(loss_rate) <= 1.0) else float(loss_rate)

    # Validate and set default for corrupt rate
    corrupt_rate = 0.0 if not (0.0 <= float(corrupt_rate) <= 1.0) else float(corrupt_rate)

    # Validate and set default for max delay
    max_delay = 0 if not (0 <= int(max_delay) <= 5) else int(max_delay)

    # Validate and set default for transmission timeout
    transmission_timeout = 3 if not (int(transmission_timeout) > 0) else int(transmission_timeout)

    # # Add this inside the start_sender function
    server_socket = establish_connection(server_ip, server_port, connection_ID, "S", loss_rate, corrupt_rate, max_delay)
    if server_socket is None:
        print("Failed to establish connection. Exiting...")
        sys.exit(1)

    try:
        with open(filename, 'r') as file:
            data = file.read(200)  # Read the first 200 bytes
            seq_num = 0

            for i in range(0, len(data), 20):  # Split data into 20-byte segments
                packet_data = data[i:i+20]
                packet = create_packet(str(seq_num), packet_data)
                # print(f"\nSending packet: {packet}")

                while True:
                    server_socket.sendall(packet.encode())
                    # print("packet:"+ packet)
                    total_packet_sent += 1
                    server_socket.settimeout(transmission_timeout)
                    try:
                        ack = server_socket.recv(30).decode()
                        total_packet_recv += 1
                        # print("recived:"+ack)
                        # print("---------------")
                        
                        if ack[2] == str(seq_num):
                            if checksum_verifier(ack):
                                seq_num = 1 - seq_num
                                break
                            else:
                                total_corrupted_pkt_recv += 1
                        else:
                            total_timeout += 1 # sender packet was corrupt so, should ignore receiver packet
                              
                    except socket.timeout:
                        total_timeout += 1
                        # break
            
            # print("\ndata:"+data)
            checksum_val = checksum(data)  # Calculate checksum of sent data
            


    except FileNotFoundError:
        print(f"File not found: {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        server_socket.close()
        print("Finish running sender: {}".format(datetime.datetime.now()))
        # PRINT STATISTICS
        print("File checksum: {}".format(checksum_val))
        print("Total packet sent: {}".format(total_packet_sent))
        print("Total packet recv: {}".format(total_packet_recv))
        print("Total corrupted packet recv: {}".format(total_corrupted_pkt_recv))
        print("Total timeout: {}".format(total_timeout))

    return (checksum_val, total_packet_sent, total_packet_recv, total_corrupted_pkt_recv, total_timeout)   

    # ##### END YOUR IMPLEMENTATION HERE #####

    # print("Finish running sender: {}".format(datetime.datetime.now()))

    # # PRINT STATISTICS
    # # PLEASE DON'T ADD ANY ADDITIONAL PRINT() AFTER THIS LINE
    # print("File checksum: {}".format(checksum_val))
    # print("Total packet sent: {}".format(total_packet_sent))
    # print("Total packet recv: {}".format(total_packet_recv))
    # print("Total corrupted packet recv: {}".format(total_corrupted_pkt_recv))
    # print("Total timeout: {}".format(total_timeout))

    # return (checksum_val, total_packet_sent, total_packet_recv, total_corrupted_pkt_recv, total_timeout)
 
if __name__ == '__main__':
    # CHECK INPUT ARGUMENTS
    if len(sys.argv) != 9:
        print("Expected \"python3 PA2_sender.py <server_ip> <server_port> <connection_id> <loss_rate> <corrupt_rate> <max_delay> <transmission_timeout> <filename>\"")
        exit()

    # ASSIGN ARGUMENTS TO VARIABLES
    server_ip, server_port, connection_ID, loss_rate, corrupt_rate, max_delay, transmission_timeout, filename = sys.argv[1:]
    
    # RUN SENDER
    start_sender(server_ip, int(server_port), connection_ID, loss_rate, corrupt_rate, max_delay, float(transmission_timeout), filename)
