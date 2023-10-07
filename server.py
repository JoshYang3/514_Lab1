### CSE514 Lab 1: P2P File Sharing ###

import socket
import threading

# Used to start the peer's server functionality
def start_server(port=9999):
    print("Starting server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)           # Create a socket object
    server_socket.bind(('0.0.0.0', port))                                       # Bind to the port
    server_socket.listen(5)                                                     # Listen for 5 maximum incoming connections
    print(f'Server listening on port {port}')

    while True:
        print("Waiting for a new connection...") 
        client_sock, addr = server_socket.accept()                              # Establish connection with client
        print(f'Connection from {addr}')
        client_handler = threading.Thread(target=handle_client, args=(client_sock, addr))  # pass addr to the function
        client_handler.start()
        

file_registry = {}                                                              # A dictionary to store all the files and their info

def handle_client(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')                  # Receive the request from the client
            if not request:                                                     # client might have disconnected
                print(f"Client {client_addr} has disconnected.")
                break
            print(f'Received: {request}')

            command, *args = request.split('|')                                 # Split the request into command and arguments

            if command == 'Register Request':
                # Process file registration
                files_info = args[1:]
                for i in range(0, len(files_info), 2):                          # Iterate through the files_info list 2 elements at a time
                    file_name, file_size = files_info[i:i+2]                    # Get the file name and size
                    file_registry[file_name] = {'size': int(file_size), 'chunks': []} # Store the file info in a dictionary
                client_socket.send(b'ACK')
            elif command == 'File List Request':
                if(file_registry == {}):                                        # If the file list is empty
                    client_socket.send('File registry is empty'.encode('utf-8'))
                else:                                                           # If the file list is not empty
                    file_list = '|'.join(file_registry.keys())                  # Get the list of files
                    client_socket.send(file_list.encode('utf-8'))               # Send the list of files to the client
            elif command == 'Disconnect':
                print(f"Received disconnect command from client {client_addr}.")
                break  # Exit the loop
    except Exception as e:
        print(f"Error occurred with client {client_addr}: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_server()

