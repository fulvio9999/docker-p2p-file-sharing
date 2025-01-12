# built-in libraries
from threading import Thread, Timer
from collections import defaultdict
import json
import datetime
import time
import warnings
warnings.filterwarnings("ignore")

# implemented classes
from utils import *
from messages.message import  Message
from messages.server2node import Server2Node
from configs import CFG, Config
config = Config.from_json(CFG)

next_call = time.time()

class Server:
    def __init__(self):
        self.server_socket = set_socket_TCP(config.constants.SERVER_ADDR[1], addr=config.constants.SERVER_ADDR[0])
        self.peers_status = defaultdict(bool)
        self.peers = defaultdict(tuple)

    def check_peers_periodically(self, interval: int):
        global next_call
        alive_nodes_ids = set()
        dead_nodes_ids = set()
        try:
            for node, has_informed in self.peers_status.items():
                if has_informed: # it means the node has informed the server that is still connected
                    self.peers_status[node] = False
                    alive_nodes_ids.add(node)
                else:
                    dead_nodes_ids.add(node)
                    self.peers_status.pop(node , None)
                    self.peers.pop(node , None)
        except RuntimeError: # the dictionary size maybe changed during iteration, so we check nodes in the next time step
            pass

        if len(dead_nodes_ids) != 0:
            log_content = f"{node} exit not intentionally."
            log(content=log_content, is_server=True, printing=True)
            log_content = f"All nodes connected in the network: {self.peers.keys()}"
            log(content=log_content, is_server=True, printing=True)

        if not (len(alive_nodes_ids) == 0 and len(dead_nodes_ids) == 0):
            log_content = f"Node(s) {list(alive_nodes_ids)} is in the network and node(s){list(dead_nodes_ids)} have left."
            log(content=log_content, is_server=True)
            
        datetime.now()
        next_call = next_call + interval
        Timer(next_call - time.time(), self.check_peers_periodically, args=(interval,)).start()
    
    def register_and_send_peers(self, conn, msg: dict, addr: tuple):
        first_time = False
        if addr[0] not in self.peers.keys():
            first_time = True
            log_content = f"Node {addr[0]} is logged in"
            log(content=log_content, is_server=True, printing=True)

        self.peers.pop(addr[0] , None)
        #send list of connected peers
        server_response = Server2Node(search_result = list(self.peers.items()))
        conn.send(server_response.encode())
        #add new peer to the list of peers
        self.peers[addr[0]] = (msg['request_port_TCP'], msg['download_port_TCP'])
        self.peers_status[addr[0]] = True
        if first_time:
            log_content = f"All nodes connected in the network: {self.peers.keys()}"
            log(content=log_content, is_server=True, printing=True)

        
    def handle_node_request(self, conn, addr: tuple):
        data = conn.recv(config.constants.TCP_BUFFER_SIZE)
        msg = Message.decode(data)
        mode = msg['mode']
        if mode == config.server_requests_mode.REGISTER:
            self.register_and_send_peers(conn, msg=msg, addr=addr)
        elif mode == config.server_requests_mode.EXIT:
            self.peers.pop(addr[0] , None)
            self.peers_status.pop(addr[0] , None)
            log_content = f"Node {addr[0]} exited intentionally."
            log(content=log_content, is_server=True, printing=True)
            log_content = f"All nodes connected in the network: {self.peers.keys()}"
            log(content=log_content, is_server=True, printing=True)
        conn.close()

    def run(self):
        log_content = f"***************** Server program started just right now! *****************"
        log(content=log_content, is_server=True)

        #timer thread to check if peers are connected
        timer_thread = Thread(target=self.check_peers_periodically, args=(config.constants.SERVER_TIME_INTERVAL,))
        timer_thread.setDaemon(True)
        timer_thread.start()

        self.server_socket.listen()
        while True:
            conn, addr = self.server_socket.accept()
            t = Thread(target=self.handle_node_request, args=(conn, addr))
            t.start()

if __name__ == '__main__':
    t = Server()
    t.run()