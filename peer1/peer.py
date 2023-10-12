import socket
import threading
import os
import random
import hashlib
import file_utils  # Import the file_utils module
from time import sleep

current_peer_port = 1111
server_ip = '127.0.0.1'
server_port = 9999
running = True
### For connecting to the server ###
# Used to connect to the server
def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket object
    client_socket.connect((server_ip, server_port))              # Connect to the server
    return client_socket                                         # Return the socket object

### sent current_peer_port to server ###
def current_peer_port_to_server(client_socket, peer_port = current_peer_port):
    
    message = f'Peer Register|{current_peer_port}' # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))                  # Send the message to the server
    response = client_socket.recv(1024).decode('utf-8')          # The server will send an ACK message if the registration is successful
    print(response, end='\n\n')
    request_connected_peers(client_socket)

# Used to register files with the server
def register_files(client_socket, peer_port=current_peer_port):
    file_name = print_out_file_in_current_folder()
    if file_name == "":
        print("No such file!")
        return
    chunk_file_paths, chunk_hashes = split_file_into_chunks(file_name)  # Split the file into chunks
    files = get_fileinfo(file_name, chunk_file_paths)  # Get file info for all chunks and the complete file
    file_info = '|'.join(f'{filename}|{file_detail["size"]}' for filename, file_detail in files.items())
    message = f'Register Request|{len(files)}|{file_info}|{peer_port}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')
    connected_peers = request_connected_peers(client_socket)
    split_info = file_info.split('|')
    file_names = split_info[::2]

    chunk_files = [item for item in file_names if '_chunk_' in item] # Extract the chunk file names
    
    num_files_to_select = len(file_names) // 4 

    for peer_port in connected_peers:
        selected_files = random.sample(chunk_files, num_files_to_select) # Randomly select 25% of the chunks to send to each peer
        for file_name in selected_files:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            full_path_file_name = os.path.join(current_dir, file_name)
            chunk_hash = chunk_hashes.get(full_path_file_name, None)
            print(chunk_hash)
            if chunk_hash is not None:
                send_chunks_to_peer(file_name, int(peer_port), chunk_hash)  # Pass the hash value if found
            else:
                print(f"Hash not found for {file_name}")

def send_chunks_to_peer(file_name, peer_port, chunk_hashes):
    if not peer_port or not str(peer_port).isdigit():
        print(f"Invalid port number: {peer_port}")
        return  # Skip to the next iteration
    if peer_port == current_peer_port:
        return
    try:
        # Create a new socket to connect to the peer
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect(('127.0.0.1', int(peer_port)))  # Assuming all peers are on the same machine
        
        # Notify the peer about the incoming file chunks
        hash_value = chunk_hashes
        
        message = f'File Chunk Offer|{file_name}|{hash_value}'
        peer_socket.send(message.encode('utf-8'))
        CHUNK_SIZE = 4096
        # Check if the peer is interested in receiving the chunks
        response = peer_socket.recv(1024).decode('utf-8')
        print(response)
        if response == 'Accept Chunk':
            #random_chunk_path = random.choice(chunk_file_paths)  # Randomly select a chunk file path
            with open(file_name, 'rb') as chunk_file:
                file_data = chunk_file.read()
                #print(file_data)
                #chunk = chunk_file.read()  # Read the entire chunk file
                send_chunk(peer_socket, file_data)
            send_chunk(peer_socket, b'EOF')
        peer_socket.close()
    except Exception as e:
        print(f"Error sending chunks to peer on port {peer_port}: {e}")

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
# Used to start the peer's server functionality in a separate thread
def start_peer_server(port=current_peer_port):
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
def get_fileinfo(filename, chunk_file_paths):
    files_info = {}

    if os.path.isfile(filename):
        file_size = os.path.getsize(filename)
        files_info[filename] = {
            'path': filename,
            'size': file_size,
        }
    
    for chunk_file_path in chunk_file_paths:  # Include chunk file info
        chunk_file_name = os.path.basename(chunk_file_path)
        chunk_file_size = os.path.getsize(chunk_file_path)
        files_info[chunk_file_name] = {
            'path': chunk_file_path,
            'size': chunk_file_size,
        }

    return files_info

# Used to handle requests from other peers
def handle_peer_request(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                break
            #print(f"Received request: {request} from {client_addr}")

            command, *args = request.split('|')
            CHUNK_SIZE = 4096
            if not args:  # Check if args list is empty
                client_socket.send("Invalid request: No arguments provided.".encode('utf-8'))
                continue

            if command == 'File Size Request':
                request_file = args[0]
                file_path = os.path.join(os.path.dirname(__file__), request_file)

                if not os.path.isfile(file_path):
                    client_socket.send("File not found.".encode('utf-8'))
                    continue  # Skip to the next iteration of the loop
                else:
                    file_size = os.path.getsize(file_path)
                    client_socket.send(str(file_size).encode('utf-8'))
                #print(f"Sent file size: {file_size} to {client_addr}")

            elif command == 'File Chunk Request':
                request_file = args[0]
                file_path = os.path.join(os.path.dirname(__file__), request_file)

                if not os.path.isfile(file_path):
                    client_socket.send("File not found.".encode('utf-8'))
                    continue  # Skip to the next iteration of the loop

                with open(file_path, 'rb') as file:
                    while True:
                        file_data = file.read(CHUNK_SIZE)
                        if not file_data:
                            break  # End of file
                        send_chunk(client_socket, file_data)
                send_chunk(client_socket, b'EOF')  # Signal end of file

            elif command == 'File Chunk Offer':
                file_name, received_hash_value = args

                client_socket.send(b'Accept Chunk')  # Indicate willingness to accept the chunk
                with open(f'{file_name}', 'wb') as f:
                    while True:
                        chunk = receive_chunk(client_socket)  # Assume receive_chunk is defined elsewhere in your code
                        if chunk == b'EOF':
                            break  # End of chunk
                        f.write(chunk)
                computed_hash_value = compute_hash(f'{file_name}')
                if computed_hash_value != received_hash_value:
                    os.remove(f'{file_name}')  # Discard the modified chunk by deleting it
                    print("Hash verification failed. Discarding chunk.")
                client_socket.send("Chunk received successfully.".encode('utf-8'))
                register_chunk_with_server(file_name, current_peer_port)

    except Exception as e:
        print(f"Error handling peer request: {e}\n\n")
    finally:
        client_socket.close()

### Used to list and select file to download ###
def list_and_select_file_to_download(client_socket):
    message = 'File List Request'                                # Create the message to send to the server
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(4096).decode('utf-8')  # increased buffer size just in case
        print("Available files:")
        for file_info in response.split('|'):
            file_name = file_info.split(" ")[0]

            index = 1;
            if not "_chunk_"in file_name:
                print(str(index) +"-"+ file_name)
                index = index+1


        user_input = input("Choose the file to download:(only enter the index of file)")

        index = 1
        valid_userinput = 0
        for file_info in response.split('|'):
            file_name = file_info.split(" ")[0]
            if not "_chunk_"in file_name:
                if str(index) == user_input:
                    valid_userinput = 1
                    print("Select "+file_name+" to download!")
                    return file_info
                index = index+1
        if valid_userinput == 0:
            return ""
    except ConnectionResetError:                                 # Handle the case where the server closes the connection
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:                                      # Handle the case where the server closes the connection
        print("Broken pipe. The server might have closed the connection.\n\n")
        return

### Used to get chunk list for a file ###
def request_file_chunk(request_file_name, client_socket):
    message = 'File List Request'                                # Create the message to send to the server
    try:
        file_chunk = []
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(4096).decode('utf-8')  # increased buffer size just in case
        print("Available files:")
        for file_info in response.split('|'):
            file_name = file_info.split(" ")[0]
            if "_chunk_"in file_name and request_file_name == file_name.split("_chunk_")[0]:
                file_chunk.append(file_info)
                print(f" - {file_info}")
        print()
        return file_chunk
    except ConnectionResetError:                                 # Handle the case where the server closes the connection
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:                                      # Handle the case where the server closes the connection
        print("Broken pipe. The server might have closed the connection.\n\n")
        return

### For downloading files ###
# Used to know the size of the file we want to download
def request_file_size_from_peer(peer_ip, peer_port, file_name):
    peer_socket = connect_to_server(peer_ip, peer_port)
    message = f'File Size Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    file_size_str = peer_socket.recv(1024).decode('utf-8')
    peer_socket.close()
    if not file_size_str.isdigit():
        raise ValueError(f"Received invalid file size: {file_size_str}")
    return int(file_size_str)

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
            if chunk == b'EOF':
                break
            downloaded_size += len(chunk)
            progress = (downloaded_size / file_size) * 100
            print(f"Download Progress: {progress:.2f}%")
            f.write(chunk)  
            
            sleep(0.5)  # introduce a delay of 0.5 seconds between chunks
            
    print(f"Downloaded {file_name} from {peer_ip}:{peer_port}")
    register_chunk_with_server(file_name, current_peer_port)
    peer_socket.close()

def register_chunk_with_server(file_name, peer_port):
    message = f'Register Chunk|{file_name}|{peer_port}'
    client_socket = connect_to_server(server_ip, server_port)
    client_socket.send(message.encode('utf-8'))
    client_socket.close()

### For user menu ###
# Used to display the menu
def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file from peer")
    print("4. Request file locations from server")
    print("5. Downloading file")
    print("6. Exit")

def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()

### Split a complete file into chunks(each chunk is 50kB) ###
def split_file_into_chunks(file_path, chunk_size=50*1024):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chunk_file_paths = []  # List to store chunk file paths
    chunk_hashes = {}  # New dictionary to store chunk hash values

    with open(file_path, 'rb') as file:
        chunk = file.read(chunk_size)
        chunk_number = 0

        while chunk:
            chunk_file_path = os.path.join(current_dir, f"{os.path.basename(file_path)}_chunk_{chunk_number}")
            with open(chunk_file_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
            chunk_file_paths.append(chunk_file_path)  # Append the chunk file path to the list
            chunk_hashes[chunk_file_path] = compute_hash(chunk_file_path)  # Compute and store hash value

            chunk_number += 1
            chunk = file.read(chunk_size)

    print(f"File '{file_path}' has been split into {chunk_number} chunks and saved in folder '{current_dir}'.")
    return chunk_file_paths, chunk_hashes  # Return the list of chunk file paths

### Request the peers that are connecting to server now ###
def request_connected_peers(client_socket):
    message = 'Connected Peers Request'                                # Create the message to send to the server
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(4096).decode('utf-8')  # increased buffer size just in case
        print("Available Peers:")
        for peers in response.split('|'):
            print(f" - {peers}")
        print()
        return response.split('|')
    except ConnectionResetError:                                 # Handle the case where the server closes the connection
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:                                      # Handle the case where the server closes the connection
        print("Broken pipe. The server might have closed the connection.\n\n")
        return
### Assemble Chunks ###
def assemble_file_from_chunks(original_filename, total_size):
    chunk_size = 50*1024
    total_chunks = -(-total_size // chunk_size)  # Calculate the total number of chunks, equivalent to math.ceil(total_size / chunk_size)

    # Check if all parts are present
    parts = [f for f in os.listdir() if f.startswith(original_filename + '_chunk_')]

    part_cal = 0
    for part in parts:
        part_flag = 0
        for part in parts:
            if part == (original_filename + '_chunk_' + str(part_cal) ):
                part_flag = 1
        if  part_flag == 0:
            print(f"Not all parts are available to assemble {original_filename}.")
            return False           
        part_cal = part_cal + 1    
    if part_cal != total_chunks:
        print(f"Not all parts are available to assemble {original_filename}.")
        return False

    # Sorting parts to ensure they are in the correct order
    parts.sort(key=lambda x: int(x.split('_chunk_')[1]))

    # If all parts are present, assemble the original file
    with open(original_filename, 'wb') as f:
        for part in parts:
            with open(part, 'rb') as p:
                f.write(p.read())

    print(f"{original_filename} has been assembled successfully.")
    return True

### Downloading file ###
def downloading_file(client_socket):
    #get file info and file name which selected by user 
    file_info = list_and_select_file_to_download(client_socket)
    file_name = file_info.split(" ")[0]
    file_size = file_info.split("size: ")[1]
    file_size = int(file_size.split(")")[0])

    #Invalid input
    if file_info == "":
        print("Invalid input!")
        return
    print(file_info)
    
    file_chunks = request_file_chunk(file_name, client_socket)
    downloading_chunks_online(file_name, file_chunks)
    assemble_file_from_chunks(file_name, file_size)

### download all the chunk online in the file ###
def downloading_chunks_online(file_name, file_chunks):
    chunks_info = {}
    for chunk_info_str in file_chunks:
        # Splitting the string to get the chunk name
        chunk_name = chunk_info_str.split(' ')[0]
        
        # Adding the chunk name to the dictionary if not already present
        if chunk_name not in chunks_info:
            chunks_info[chunk_name] = []
        
        # Finding the index of 'peers:' to later extract the peer info
        peer_info_start_idx = chunk_info_str.find('peers: ')
        
        if peer_info_start_idx != -1:
            # Extracting the peer info substring
            peer_info_str = chunk_info_str[peer_info_start_idx + len('peers: '):]
            # Splitting the peer info string into individual peer info
            peer_info_list = peer_info_str.split(', ')
            # Adding the peer info to the corresponding chunk in the dictionary
            chunks_info[chunk_name].extend(peer_info_list)
    print(chunks_info)

    for chunk_name, peer_info_list in chunks_info.items():
        print(chunk_name)
        for peer_info in peer_info_list:
            # Split the peer info into IP and port
            peer_ip, peer_port = peer_info.split(':')
            if peer_port == str(current_peer_port):
                continue
            else:
                download_file_from_peer(chunk_name, peer_ip, int(peer_port))
                break

    '''
    max_index = 0
    for chunk in file_chunks:
        file_name = chunk.split(" ")[0]
        index = file_name.split("_chunk_")[1]
        if int(index) > max_index:
            max_index = int(index)

    index = 0
    for index in range(0,max_index+1):
        for chunk in file_chunks: 
            print(chunk)
            file_name = chunk.split(" ")[0]
            peer_port = chunk.split("peers: ")[1]
            print(peer_port)
            peer_info = peer_port.split(":")  # Split by comma and space
            print(peer_info)
            peer_ip = peer_info[0]  # Get the IP address
            peer_port_num = int(peer_info[1])
            #print("_chunk_"+str(index))
            #print(file_name)
            if ("_chunk_"+str(index)) in file_name:
                download_file_from_peer(file_name, peer_ip, peer_port_num)
                continue
        print(index)'''

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

    file_name = ""
    j = 1
    for file in files:
        if str(j) == user_input:
            file_name = file
            split_file_into_chunks(file)
        j += 1
    
    return file_name
    
    
###
### Main function ###
def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create a socket object

    # Connect to the server
    #server_ip = '127.0.0.1'
    #server_port = 9999
    peer_ip = '127.0.0.1'
    client_socket.connect((server_ip, server_port))

    # Start the peer's server functionality in a separate thread
    threading.Thread(target=start_peer_server).start()
    
    flag_peer_port = 0
    while True:
        if flag_peer_port == 0:
            current_peer_port_to_server(client_socket, peer_port = current_peer_port)
            
            flag_peer_port = 1

        display_menu()                                                  # Display the menu at the start of each loop iteration
        user_input = input("Enter the number of your choice: ")

        if user_input == '1':
            register_files(client_socket, peer_port=current_peer_port)
        
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
            downloading_file(client_socket)

        elif user_input == '6':
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

    
