### CSE514 Lab 1: P2P File Sharing ###

import socket
import threading
import time
import pickle as pk

class Server(threading.Thread):
    def __init__(self, max_connections, port):
        self.host = 'localhost'
