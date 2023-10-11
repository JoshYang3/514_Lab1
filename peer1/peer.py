import socket
import threading
import os
import file_utils  # Import the file_utils module
from time import sleep


### For connecting to the server ###
# Used to connect to the server
def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket object
    client_socket.connect((server_ip, server_port))              # Connect to the server
    return client_socket                                         # Return the socket object

# Used to register files with the server
def register_files(client_socket, files, peer_port = 1111):
    print_out_file_in_current_folder()
    file_info = '|'.join(f'{filename}|{file_detail["size"]}' for filename, file_detail in files.items()) # Create a string of file info
    message = f'Register Request|{len(files)}|{file_info}|{peer_port}' # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))                  # Send the message to the server
    response = client_socket.recv(1024).decode('utf-8')          # The server will send an ACK message if the registration is successful
    print(response, end='\n\n')

# Used to request the list of files from the server
def request_file_list(client_socket):
    message = 'File List Request'                                # Create the message to send to the server
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(4096).decode('utf-8')  # increased buffer size just in case
        print("Available files:")
        for file_info in response.split('|'):
            print(f" - {file_info}")
        print()
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
    chunk_size = int.from_bytes(socket.recv(4), byteorder='big')
    chunk = b""
    while len(chunk) < chunk_size:
        part = socket.recv(chunk_size - len(chunk))
        if not part:
            break  # socket connection broken
        chunk += part
    return chunk

# Used to search for files in the file registry, assume the response is a list of IPs and ports.
def request_file_locations(client_socket, file_name): 
    message = f'File Locations Request|{file_name}'             # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    
    if 'File not found.' in response:
        print(f"The file '{file_name}' was not found on the server.\n")
        return []

    file_info, *peers_ports = response.split('|')
    print(f"File '{file_info}' is available at the following peer ports: {', '.join(peers_ports)}\n")
    return peers_ports                                          # Assume the response is a list of IPs and ports.

### For other peers connecting ###
running = True
# Used to start the peer's server functionality in a separate thread
def start_peer_server(port=1111):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    server_socket.settimeout(1)  # Set a timeout of 1 second

    while running:
        try:
            client_sock, addr = server_socket.accept()
            client_handler = threading.Thread(target=handle_peer_request, args=(client_sock, addr))
            client_handler.start()
        except socket.timeout:
            pass

    server_socket.close()

# Used to tell the server that what file chunks we have
def get_files_in_current_directory():
    files_info = {}
    directory_path = os.path.dirname(os.path.abspath(__file__))
    exclude_files = ['utils.py', 'file_utils.py', 'peer.py']    # Files to exclude from the file registry

    for filename in os.listdir(directory_path):                 # Iterate through all files in the current directory
        if filename in exclude_files:                           # Skip the excluded files
            continue

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
            CHUNK_SIZE = 4096  # Define a size for the chunks (e.g., 4KB)
            if command == 'File Size Request':
                request_file = args[0]
                file_info = file_list.get(request_file)
                if file_info:
                    file_size = str(file_info['size'])
                    client_socket.send(file_size.encode('utf-8'))
                else:
                    client_socket.send(b'0')
            # In handle_peer_request:
            elif command == 'File Chunk Request':
                request_file = args[0]
                file_info = file_list.get(request_file)
                if file_info:
                    with open(file_info['path'], 'rb') as file:
                        while True:
                            file_data = file.read(CHUNK_SIZE)
                            if not file_data:
                                break
                            send_chunk(client_socket, file_data)
                    send_chunk(client_socket, b'')  # Indicate end of file data
                else:
                    client_socket.send("File not found.".encode('utf-8'))  # Send an error message if the file isn't found            # Send empty chunk to indicate end of file
            
    except Exception as e:                                      # Handle any errors that might occur
        print(f"Error handling peer request: {e}\n\n")
    finally:                                                    # Close the socket when done
        client_socket.close()

### For downloading files ###
# Used to know the size of the file we want to download
def request_file_size_from_peer(peer_ip, peer_port, file_name):
    peer_socket = connect_to_server(peer_ip, peer_port)
    message = f'File Size Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    file_size = int(peer_socket.recv(1024).decode('utf-8'))  # Expect the file size as a plain number
    peer_socket.close()
    return file_size


# Used to download a file from a peer
def download_file_from_peer(file_name, peer_ip, peer_port):
    file_size = request_file_size_from_peer(peer_ip, peer_port, file_name)
    peer_socket = connect_to_server(peer_ip, peer_port)
    message = f'File Chunk Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    
    downloaded_size = 0
    with open(file_name, 'wb') as f:
        while True:
            chunk = receive_chunk(peer_socket)
            if not chunk:
                break
            downloaded_size += len(chunk)
            progress = (downloaded_size / file_size) * 100
            print(f"Download Progress: {progress:.2f}%")
            f.write(chunk)  
            
            sleep(0.5)  # introduce a delay of 0.5 seconds between chunks
            
    print(f"Downloaded {file_name} from {peer_ip}:{peer_port}")
    peer_socket.close()

### For user menu ###
# Used to display the menu
def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file from peer")
    print("4. Request file locations from server")
    print("5. Exit")

### Split a complete file into chunks(each chunk is 50) ###
def split_file_into_chunks(file_path, chunk_size=50*1024):
    # Make a new directory called file_name
    dir_name = "_"+file_path
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    with open(file_path, 'rb') as file:
        chunk = file.read(chunk_size)
        chunk_number = 0
        
        while chunk:
            chunk_file_path = os.path.join(dir_name, f"{os.path.basename(file_path)}_chunk_{chunk_number}")
            with open(chunk_file_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
            
            chunk_number += 1
            chunk = file.read(chunk_size)
        
        print(f"File '{file_path}' has been split into {chunk_number} chunks and saved in folder '{dir_name}'.")


    '''with open(file_path, 'rb') as file:
        chunk = file.read(chunk_size)
        chunk_number = 0
        
        while chunk:
            with open(f"{file_path}_chunk_{chunk_number}", 'wb') as chunk_file:
                chunk_file.write(chunk)
            
            chunk_number += 1
            chunk = file.read(chunk_size)
        
        print(f"File '{file_path}' has been split into {chunk_number} chunks.")'''

### Print out all the file under current folder ###
def print_out_file_in_current_folder():
    
    folder_path = ''
        
    # Get all files and folders in the current directory
    all_items = os.listdir()
    # Filter out the items to get only files
    files = [item for item in all_items if os.path.isfile(item)]
    # Print the name of each file
    
    i = 1
    for file in files:
        print(str(i)+"."+file)
        i += 1
        
    
    # Choose file
    user_input = input("Choose file to register:(only input the number)")
    print("")

    j = 1
    for file in files:
        if str(j) == user_input:
            split_file_into_chunks(file)
        j += 1

    
    

###
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
            register_files(client_socket, file_list, peer_port=1111)
        
        elif user_input == '2':
            request_file_list(client_socket)
        
        elif user_input == '3':
            peer_port = int(input("Enter the port of the peer to download from: "))
            file_name = input("Enter the name of the file to download: ")
            download_file_from_peer(file_name, peer_ip, peer_port)
        
        elif user_input == '4':
            file_name = input("Enter the name of the file you want to locate: ")
            request_file_locations(client_socket, file_name)
        
        elif user_input == '5':
            print("Disconnecting...")
            global running
            running = False  # Signal the peer server to stop
            disconnect(client_socket)
            break  # Exit the loop
        
        else:
            print("Invalid choice, please try again.")

    # Disconnect from the server
    client_socket.close()

if __name__ == "__main__":
    main()

    
