import socket
import threading

def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    return client_socket

def register_files(client_socket, files):
    file_info = '|'.join(f'{file["name"]},{file["size"]}' for file in files)
    message = f'Register Request:{len(files)}|{file_info}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)

def request_file_list(client_socket):
    message = 'File List Request'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)

def main():
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    server_ip = '127.0.0.1'
    server_port = 9999
    client_socket.connect((server_ip, server_port))

    # Create a list of files to register
    files = [
        {"name": "file1.txt", "size": 12345},
        {"name": "file2.txt", "size": 67890}
    ]

    # Call the register_files function
    register_files(client_socket, files)
    request_file_list(client_socket)

    # Close the socket when done
    client_socket.close()

if __name__ == "__main__":
    main()
    client_socket = connect_to_server("127.0.0.1", 9999)  # use the correct IP and port
    files = [{"name": "test1", "size": 12345}]  # example files list
    register_files(client_socket, files)
    request_file_list(client_socket)
    
