import socket
import threading
import os
import file_utils  # Import the file_utils module

### For connecting to the server ###
# Used to connect to the server
def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket object
    client_socket.connect((server_ip, server_port))              # Connect to the server
    return client_socket                                         # Return the socket object

# Used to register files with the server
def register_files(client_socket, files):
    file_info = '|'.join(f'{filename}|{file_detail["size"]}' for filename, file_detail in files.items()) # Create a string of file info
    message = f'Register Request|{len(files)}|{file_info}'       # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))                  # Send the message to the server
    response = client_socket.recv(1024).decode('utf-8')          # The server will send an ACK message if the registration is successful
    print(response, end='\n\n')

# Used to request the list of files from the server
def request_file_list(client_socket):
    message = 'File List Request'                                # Create the message to send to the server
    try:
        client_socket.send(message.encode('utf-8')) 
        response = client_socket.recv(1024).decode('utf-8')
        print(response, end='\n\n')
    except ConnectionResetError:                                 # Handle the case where the server closes the connection
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:                                      # Handle the case where the server closes the connection
        print("Broken pipe. The server might have closed the connection.\n\n")
        return

# Used to disconnect from the server
def disconnect(client_socket):
    message = 'Disconnect'                                       # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')

# Used to send a chunk of data over the socket
def send_chunk(socket, chunk):
    socket.sendall(len(chunk).to_bytes(4, byteorder='big'))      # Send the size of the chunk first
    socket.sendall(chunk)                                        # Send the chunk

# Used to receive a chunk of data from the socket
def receive_chunk(socket):
    chunk_size = int.from_bytes(socket.recv(4), byteorder='big') # Receive the size of the chunk first
    chunk = socket.recv(chunk_size)                              # Receive the chunk
    return chunk

# Used to search for files in the file registry, assume the response is a list of IPs and ports.
def request_file_locations(client_socket, file_name): 
    message = f'File Locations Request|{file_name}'             # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    return response.split('|')                                  # Assume the response is a list of IPs and ports.

### For other peers connecting ###
# Used to start the peer's server functionality in a separate thread
def start_peer_server(port=3333):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)

    while True:
        client_sock, addr = server_socket.accept()
        client_handler = threading.Thread(target=handle_peer_request, args=(client_sock, addr))
        client_handler.start()

# Used to tell the server that what file chunks we have
def get_files_in_current_directory():
    files_info = {}
    directory_path = os.path.dirname(os.path.abspath(__file__))

    for filename in os.listdir(directory_path):                 # Iterate through all files in the current directory
        filepath = os.path.join(directory_path, filename)
        
        if os.path.isfile(filepath):
            file_size = os.path.getsize(filepath)
            files_info[filename] = {                            # Store the file info in a dictionary
                'path': filepath,                               # full path to the file
                'size': file_size,                              # size of the file
            }

    return files_info

file_list = get_files_in_current_directory()                    # A dictionary to store file info and chunks

# Used to handle requests from other peers
def handle_peer_request(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:                                     # client might have disconnected
                #print(f"Client {client_addr} has disconnected.\n\n")
                break
            #print(f'Received: {request}\n\n')

            command, *args = request.split('|')                 # Split the request into command and arguments

            if command == 'File Chunk Request':
                request_file = args[0]                          # Filename is extracted from the request
                file_info = file_list.get(request_file)         # Search for the file in the file registry this peer has
                if file_info:                                   # If the file is found
                    with open(file_info['path'], 'rb') as file: # Open the file in binary mode
                        file_data = file.read()                 # Read the file
                        send_chunk(client_socket, file_data)    # Send the file data to the requesting peer
                    send_chunk(client_socket, b'')              # Send empty chunk to indicate end of file
                else:
                    error_message = "File not found."           # Inform the requesting peer that we don't have the file.
                    client_socket.send(error_message.encode('utf-8'))
    except Exception as e:                                      # Handle any errors that might occur
        print(f"Error handling peer request: {e}\n\n")
    finally:                                                    # Close the socket when done
        client_socket.close()

### For downloading files ###
# Used to download a file from a peer
def download_file_from_peer(file_name, peer_ip, peer_port):
    peer_socket = connect_to_server(peer_ip, peer_port)         # Reuse the connect_to_server function
    message = f'File Chunk Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    
    with open(file_name, 'wb') as f:                            # Open file for writing in binary mode
        while True:                                             # Keep reading chunks till the file is completely received
            chunk = receive_chunk(peer_socket)
            if not chunk:                                       # If chunk is empty, it means the entire file has been received
                break
            f.write(chunk)                                      # Write the chunk to the file

    print(f"Downloaded {file_name} from {peer_ip}:{peer_port}")
    peer_socket.close()

### For user menu ###
# Used to display the menu
def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file from peer")
    print("4. Exit")
    
### Split a complete file into chunks(each chunk is 50) ###
def split_file_into_chunks(file_path, chunk_size=50*1024):
    with open(file_path, 'rb') as file:
        chunk = file.read(chunk_size)
        chunk_number = 0
        
        while chunk:
            with open(f"{file_path}_chunk_{chunk_number}", 'wb') as chunk_file:
                chunk_file.write(chunk)
            
            chunk_number += 1
            chunk = file.read(chunk_size)
        
        print(f"File '{file_path}' has been split into {chunk_number} chunks.")

### Main function ###
def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create a socket object

    # Connect to the server
    server_ip = '127.0.0.1'
    server_port = 9999
    peer_ip = '127.0.0.1'
    client_socket.connect((server_ip, server_port))

    # Start the peer's server functionality in a separate thread
    threading.Thread(target=start_peer_server).start()

    while True:
        display_menu()                                                  # Display the menu at the start of each loop iteration
        user_input = input("Enter the number of your choice: ")

        if user_input == '1':
            register_files(client_socket, file_list)
        
        elif user_input == '2':
            request_file_list(client_socket)
        
        elif user_input == '3':
            peer_port = int(input("Enter the port of the peer to download from: "))
            file_name = input("Enter the name of the file to download: ")
            download_file_from_peer(file_name, peer_ip, peer_port)
        
        elif user_input == '4':
            print("Disconnecting...")
            disconnect(client_socket)
            break  # Exit the loop
        
        else:
            print("Invalid choice, please try again.")

    # Disconnect from the server
    client_socket.close()

if __name__ == "__main__":
    main()

    
