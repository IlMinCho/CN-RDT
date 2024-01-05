#!/usr/bin/env python3
# Last updated: Oct, 2021

import sys
import time
import socket
import datetime 
from checksum import checksum, checksum_verifier

CONNECTION_TIMEOUT = 60 # timeout when the receiver cannot find the sender within 60 seconds
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

def create_ack_packet(ack_num):
    """ Creates an ACK packet with the given acknowledgment number """
    ack_packet = f"  {ack_num} {' ' * 20} "  # Data field is blank in ACK packet
    ack_packet_checksum = checksum(ack_packet)
    return f"{ack_packet}{ack_packet_checksum}"


def start_receiver(server_ip, server_port, connection_ID, loss_rate=0.0, corrupt_rate=0.0, max_delay=0.0):
    """
     This function runs the receiver, connnect to the server, and receiver file from the sender.
     The function will print the checksum of the received file at the end. 
     The checksum is expected to be the same as the checksum that the sender prints at the end.

     Input: 
        server_ip - IP of the server (String)
        server_port - Port to connect on the server (int)
        connection_ID - your sender and receiver should specify the same connection ID (String)
        loss_rate - the probabilities that a message will be lost (float - default is 0, the value should be between 0 to 1)
        corrupt_rate - the probabilities that a message will be corrupted (float - default is 0, the value should be between 0 to 1)
        max_delay - maximum delay for your packet at the server (int - default is 0, the value should be between 0 to 5)

     Output: 
        checksum_val - the checksum value of the file sent (String that always has 5 digits)
    """

    print("Student name: {} {}".format(FIRST_NAME, LAST_NAME))
    print("Start running receiver: {}".format(datetime.datetime.now()))

    checksum_val = "00000"
    received_data = ""
    expected_seq_num = 0
    last_ack_sent = 1

    ##### START YOUR IMPLEMENTATION HERE #####
    loss_rate = 0.0 if not (0.0 <= float(loss_rate) <= 1.0) else float(loss_rate)

    # Validate and set default for corrupt rate
    corrupt_rate = 0.0 if not (0.0 <= float(corrupt_rate) <= 1.0) else float(corrupt_rate)

    # Validate and set default for max delay
    max_delay = 0 if not (0 <= int(max_delay) <= 5) else int(max_delay)



    # Add this inside the start_receiver function
    server_socket = establish_connection(server_ip, server_port, connection_ID, "R", loss_rate, corrupt_rate, max_delay)
    if server_socket is None:
        print("Failed to establish connection. Exiting...")
        sys.exit(1)

    try:
        while True:
            packet = server_socket.recv(30).decode()
            # print("\nreceived:"+packet)

            # Check if the packet has enough data to be unpacked
            if packet == '':
                print("Connection closed by sender.")
                break
            if len(packet) < 30:
                print("Incomplete packet received. Length:", len(packet))
                continue

            # Extract sequence number, payload, and checksum
            parts = packet.split(' ')
            seq_num = parts[0]
            payload = packet[4:-6] # Join back the payload part
            packet_checksum = parts[-1]

            calculated_checksum = checksum(f"{seq_num} 0 {payload} ")

            # print(calculated_checksum)
            # print(packet_checksum)
            # print(seq_num)
            # print(expected_seq_num)

            if calculated_checksum == packet_checksum and str(seq_num) == str(expected_seq_num):
                received_data += payload
                last_ack_sent = expected_seq_num
                ack_packet = create_ack_packet(expected_seq_num)
                # print("1")

                expected_seq_num = 1 - expected_seq_num
            elif calculated_checksum != packet_checksum or seq_num != last_ack_sent:
                ack_packet = create_ack_packet(last_ack_sent)
                # print("2")

            server_socket.send(ack_packet.encode())
            
        #     print("sent:"+ack_packet)

        # print(len(received_data))
        # print("last:"+str(received_data))
        checksum_val = checksum(received_data)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        server_socket.close()
        print("Finish running receiver: {}".format(datetime.datetime.now()))
        print("File checksum: {}".format(checksum_val))

    return checksum_val

    # ##### END YOUR IMPLEMENTATION HERE #####

    # print("Finish running receiver: {}".format(datetime.datetime.now()))

    # # PRINT STATISTICS
    # # PLEASE DON'T ADD ANY ADDITIONAL PRINT() AFTER THIS LINE
    # print("File checksum: {}".format(checksum_val))

    # return checksum_val

 
if __name__ == '__main__':
    # CHECK INPUT ARGUMENTS
    if len(sys.argv) != 7:
        print("Expected \"python PA2_receiver.py <server_ip> <server_port> <connection_id> <loss_rate> <corrupt_rate> <max_delay>\"")
        exit()
    server_ip, server_port, connection_ID, loss_rate, corrupt_rate, max_delay = sys.argv[1:]
    # START RECEIVER
    start_receiver(server_ip, int(server_port), connection_ID, loss_rate, corrupt_rate, max_delay)
