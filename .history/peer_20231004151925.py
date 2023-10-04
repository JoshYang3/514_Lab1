import socket
import threading

def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    return client_socket

def register_files(client_socket, files):
    message = f'Register Request:{len(files)}|' + '|'.join(files)
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)

def request_file_list(client_socket):
    message = 'File List Request'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)
