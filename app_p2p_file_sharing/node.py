# built-in libraries
from cmath import e
from multiprocessing import Event
from socket import timeout
from messages.chunk_sharing import ChunkSharing
from utils import *
import argparse
from threading import Thread, Timer
from operator import itemgetter
import datetime
import time
from itertools import groupby
import mmap
import warnings
warnings.filterwarnings("ignore")
from threading import current_thread

# implemented classes
from configs import CFG, Config
config = Config.from_json(CFG)
from messages.message import Message
from messages.node2server import Node2Server
from messages.node2node import Node2Node

next_call = time.time()

class Node:
    def __init__(self, request_port_TCP: int, download_port_TCP: int):
        self.request_port_TCP = request_port_TCP
        self.ip_addr = socket.gethostbyname(socket.gethostname())
        self.request_socket = set_socket_TCP(request_port_TCP, addr=self.ip_addr)
        self.download_port_TCP = download_port_TCP
        self.download_socket = set_socket_TCP(download_port_TCP, addr=self.ip_addr)
        self.peers = []
        self.download_threads = []
        self.upload_threads = []
        self.downloaded_files = {}
    

    def receive_chunk(self, filename: str, range: tuple, file_owner: tuple):
        udp_port = generate_random_port()
        msg = Node2Node(filename=filename, mode=config.node_requests_mode.CHUNKS, range=range, portUDP=udp_port)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(file_owner)
        client.send(msg.encode())
        #client.close()

        log_content = f"I sent a request for a chunk of {filename} for node {file_owner[0]}"
        log(content=log_content)

        temp_sock = set_socket_UDP(udp_port, addr=self.ip_addr)

        while True:
            data, addr = temp_sock.recvfrom(config.constants.UDP_BUFFER_SIZE)
            msg = Message.decode(data)
            if msg["idx"] == -1: # end of the file
                client.send(data)
                free_socket(temp_sock)
                client.close()
                return
            self.downloaded_files[filename].append(msg)

    def split_file_to_chunks(self, file_path: str, rng: tuple) -> list:
        with open(file_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)[rng[0]: rng[1]]
            # we divide each chunk to a fixed-size pieces to be transferable
            piece_size = config.constants.CHUNK_PIECES_SIZE
            return [mm[p: p + piece_size] for p in range(0, rng[1] - rng[0], piece_size)]

    def send_chunk(self, msg, ip_addr_dest, conn):
        filename = msg['filename']
        range = msg['range']
        dest_port = msg['portUDP']
        file_path = f"{config.directory.node_files_dir}{filename}"
        chunk_pieces = self.split_file_to_chunks(file_path=file_path, rng=range)

        client = set_socket_UDP(generate_random_port(), addr=self.ip_addr)
        for idx, p in enumerate(chunk_pieces):
            msg = ChunkSharing(filename=filename, range=range, idx=idx, chunk=p)
            client.sendto(Message.encode(msg), (ip_addr_dest, dest_port))
        # tell the node that sending has finished (idx = -1)
        msg = ChunkSharing(filename=filename,range=range)
        conn.settimeout(2.0)
        while True:
            client.sendto(Message.encode(msg), (ip_addr_dest, dest_port))
            try:
                data = conn.recv(config.constants.TCP_BUFFER_SIZE)
                break
            except timeout:
                pass

        log_content = f"The process of sending a chunk to node '{ip_addr_dest}' of file {filename} has finished!"
        log(content=log_content)
        conn.close()
        free_socket(client)
        self.upload_threads.remove(current_thread())

    def sort_downloaded_chunks(self, filename: str) -> list:
        sort_result_by_range = sorted(self.downloaded_files[filename], key=itemgetter("range"))
        group_by_range = groupby(sort_result_by_range, key=lambda i: i["range"])
        sorted_downloaded_chunks = []
        for key, value in group_by_range:
            value_sorted_by_idx = sorted(list(value), key=itemgetter("idx"))
            sorted_downloaded_chunks.append(value_sorted_by_idx)

        return sorted_downloaded_chunks

    def reassemble_file(self, chunks: list, file_path: str):
        with open(file_path, "bw+") as f:
            for ch in chunks:
                f.write(ch)
            f.flush()
            f.close()

    def start_download_chunks(self, file_owners, filename):
        # 2. Ask file size
        file_size = self.ask_file_size(filename=filename, file_owners=file_owners)
        if file_size == 0:
            content_log = f"ERROR to get file size of '{filename}'"
            log(content=content_log, printing=True)
            return
        log_content = f"The file '{filename}' which you are about to download, has size of {file_size} bytes"
        log(content=log_content, printing=True)

        # 2. Split file equally among nodes to download chunks of it from them
        step = file_size / len(file_owners)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(file_owners))]

        # 3. Create a thread for each node to get a chunk from it
        self.downloaded_files[filename] = []
        neighboring_peers_threads = []
        for idx, obj in enumerate(file_owners):
            t = Thread(target=self.receive_chunk, args=(filename, chunks_ranges[idx], obj))
            t.setDaemon(True)
            t.start()
            neighboring_peers_threads.append(t)
        for t in neighboring_peers_threads:
            t.join()

        log_content = f"All the chunks of '{filename}' has downloaded from neighboring peers. But they must be reassembled!"
        log(content=log_content)

        # 4. Sort chunks of file.
        sorted_chunks = self.sort_downloaded_chunks(filename=filename)
        log_content = f"All chunks of the '{filename}' is now sorted and ready to be reassembled."
        log(content=log_content)

        # 5. Assemble the chunks to re-build the file
        total_file = []
        file_path = f"{config.directory.node_files_dir}{filename}"
        for chunk in sorted_chunks:
            for piece in chunk:
                total_file.append(piece["chunk"])
        self.reassemble_file(chunks=total_file, file_path=file_path)
        log_content = f"'{filename}' has successfully downloaded and saved in my files directory."
        log(content=log_content, printing=True) 
        
        self.download_threads.remove(current_thread())

    def start_download(self, file_owner, filename):
        peer_addr, peer_download_port_TCP = file_owner
        msg = Node2Node(filename=filename)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((peer_addr, peer_download_port_TCP))
        client.send(msg.encode())
        
        file_path = f"{config.directory.node_files_dir}{filename}"
        file = open(file_path, "wb")

         # Receive any data from client side
        recv_data = client.recv(config.constants.TCP_BUFFER_SIZE)
        while recv_data:
            file.write(recv_data)
            recv_data = client.recv(config.constants.TCP_BUFFER_SIZE)
        file.close()
        client.close()
        self.download_threads.remove(current_thread())
        content_log = f"'{filename}' downloaded with success from {file_owner[0]}"
        log(content=content_log, printing=True)

    def get_pos_node(self, file_owners):
        try:
            pos = int(input())
        except ValueError:
            pos=-10
        while pos<0 or pos>= len(file_owners):
            if pos==-1 or pos==-2:
                return pos
            print("Error! Insert the position again of the array (-1 to cancel; -2 to download chunks):")
            try:
                pos = int(input())
            except ValueError:
                pos=-10
        return pos

    def download(self, filename: str):
        file_path = f"{config.directory.node_files_dir}{filename}"
        if os.path.isfile(file_path):
            log_content = f"You already have this file!"
            log(content=log_content, printing=True)
            return
        else:
            log_content = f"You just started to download {filename}. Let's search it in the network!"
            log(content=log_content)
            file_owners = self.search_file_owners(filename=filename)
            if len(file_owners)>0:
                log_content = f"'{filename}' found in nodes: {[ip for (ip,_) in file_owners]}"
                log(content=log_content, printing=True)
                print(f"CHOOSE THE NODE FOR DOWNLOADING '{filename}'.")
                print("Insert the position of the array (-1 to cancel; -2 to download chunks):")

                pos = self.get_pos_node(file_owners)
                if pos == -1:
                    log_content = f"Downloading canceled!"
                    log(content=log_content, printing=True)
                    return 
                
                if pos == -2:
                    log_content = f"Start download chunks of '{filename}' from {[ip for (ip,_) in file_owners]}."
                    log(content=log_content, printing=True)
                    t = Thread(target=self.start_download_chunks, args=(file_owners, filename,))
                    t.setDaemon(True)
                    t.start()
                    self.download_threads.append(t)
                    return 

                log_content = f"Start download '{filename}' from {file_owners[pos][0]}."
                log(content=log_content, printing=True)
                t = Thread(target=self.start_download, args=(file_owners[pos], filename,))
                t.setDaemon(True)
                t.start()
                self.download_threads.append(t)
            else:
                log_content = f"'{filename}' not found in the network."
                log(content=log_content, printing=True)

    def search_file_owners(self, filename: str):
        file_owners = []
        for (peer_addr, (peer_req_port_TCP, peer_download_port_TCP)) in self.peers:
            msg = Node2Node(filename=filename)
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((peer_addr, peer_req_port_TCP))
                client.send(msg.encode())
                data = client.recv(config.constants.TCP_BUFFER_SIZE)
                server_msg = Message.decode(data)
                if server_msg['filename'] != '':
                    file_owners.append((peer_addr, peer_download_port_TCP))
                client.close()
            except ConnectionRefusedError:
                log_content = f"Unable to connect to {peer_addr}"
                log(content=log_content, printing=True)
            
        return file_owners


    def fetch_owned_files(self) -> list:
        files = []
        node_files_dir = config.directory.node_files_dir
        if os.path.isdir(node_files_dir):
            _, _, files = next(os.walk(node_files_dir))
        else:
            os.makedirs(node_files_dir)

        return files
    
    def check_file(self, conn, addr: tuple):
        data = conn.recv(config.constants.TCP_BUFFER_SIZE)
        msg = Message.decode(data)
        filename = msg['filename']
        if filename not in self.fetch_owned_files():
            content_log = f"You don't have '{filename}' request from {addr}"
            log(content=content_log)
            filename = ''

        msg = Node2Node(filename=filename)
        conn.send(msg.encode())
        conn.close()


    def send_file(self, conn, msg):
        filename = msg['filename']
        file_path = f"{config.directory.node_files_dir}{filename}"
        file = open(file_path, "rb")

        send_data = file.read(config.constants.TCP_BUFFER_SIZE)
        while send_data:
            conn.send(send_data)
            send_data = file.read(config.constants.TCP_BUFFER_SIZE)      
        file.close()
        conn.close()
        self.upload_threads.remove(current_thread())

    def ask_file_size(self, filename: str, file_owners) -> int:
        msg = Node2Node(filename=filename, mode=config.node_requests_mode.SIZE)
        size=0
        for file_owner in file_owners:
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(file_owner)
                client.send(msg.encode())
                data = client.recv(config.constants.TCP_BUFFER_SIZE)
                server_msg = Message.decode(data)
                size = server_msg['size']
                client.close()
            except ConnectionRefusedError:
                log_content = f"Unable to connect to {file_owner[0]} for request of file size."
                log(content=log_content)
        return size

    def tell_file_size(self, msg, conn):
        filename = msg['filename']
        file_path = f"{config.directory.node_files_dir}{filename}"
        file_size = os.stat(file_path).st_size
        response_msg = Node2Node(filename=filename, size=file_size)
        conn.send(response_msg.encode())     
        conn.close()
        if current_thread() in self.upload_threads: self.upload_threads.remove(current_thread())

    def inform_server_periodically(self, interval: int):
        global next_call
        self.enter_network(f"I informed the server that I'm still alive!")

        datetime.datetime.now()
        next_call = next_call + interval
        Timer(next_call - time.time(), self.inform_server_periodically, args=(interval,)).start()

    def receive_request_download_from_nodes(self):
        self.download_socket.listen()
        while True:
            conn, addr = self.download_socket.accept()
            data = conn.recv(config.constants.TCP_BUFFER_SIZE)
            msg = Message.decode(data)
            if msg['mode'] == config.node_requests_mode.SIZE:
                t = Thread(target=self.tell_file_size, args=(msg, conn,))
            elif msg['mode'] == config.node_requests_mode.CHUNKS:
                t = Thread(target=self.send_chunk, args=(msg, addr[0], conn,))
            else:#download
                t = Thread(target=self.send_file, args=(conn, msg,))
            t.start()
            self.upload_threads.append(t)            
        
    
    def receive_request_search_from_nodes(self):
        self.request_socket.listen()
        while True:
            conn, addr = self.request_socket.accept()
            t = Thread(target=self.check_file, args=(conn, addr,))
            t.start()
            

    def exit_network(self):
        wait_download_threads = self.download_threads.copy()
        wait_upload_threads = self.upload_threads.copy()
        if len(self.download_threads) > 0:
            log_content = f"Waiting download of {len(self.download_threads)} file/s..."
            log(content=log_content, printing=True)
        if len(self.upload_threads) > 0:
            log_content = f"Waiting upload of {len(self.upload_threads)} file/s..."
            log(content=log_content, printing=True)
        for t in wait_download_threads:
            t.join()
        for t in wait_upload_threads:
            t.join()

        msg = Node2Server(mode=config.server_requests_mode.EXIT,
                          request_port_TCP=self.request_port_TCP,
                          download_port_TCP=self.download_port_TCP)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(tuple(config.constants.SERVER_ADDR))
        client.send(msg.encode())
        client.close()

        log_content = f"You exited the torrent!"
        log(content=log_content)

    def enter_network(self, log_content):
        msg = Node2Server(mode=config.server_requests_mode.REGISTER,
                          request_port_TCP = self.request_port_TCP,
                          download_port_TCP=self.download_port_TCP)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(tuple(config.constants.SERVER_ADDR))
        client.send(msg.encode())

        log(content=log_content)

        data = client.recv(config.constants.TCP_BUFFER_SIZE)
        server_msg = Message.decode(data)
        self.peers = server_msg['search_result']
        if log_content == "You entered.":
            log_content = f"Nodes connected to the network: {[a for a,b in self.peers]}"
            log(content=log_content, printing=True)
        client.close()


    def run(self):
        log_content = f"***************** Node program started just right now! *****************"
        log(content=log_content)
        print(f"****** START {self.ip_addr} ******")
        node.enter_network(f"You entered.")

        # Create a thread to periodically informs the server to tell it is still connected.
        timer_thread = Thread(target=node.inform_server_periodically, args=(config.constants.NODE_TIME_INTERVAL,))
        timer_thread.setDaemon(True)
        timer_thread.start()

        # Create a thread to listen request of looking for a file from others peers.
        request_thread = Thread(target=node.receive_request_search_from_nodes, args=())
        request_thread.setDaemon(True)
        request_thread.start()

        # Create a thread to listen request of download a file from others peers.
        download_thread = Thread(target=node.receive_request_download_from_nodes, args=())
        download_thread.setDaemon(True)
        download_thread.start()

        while True:
            print("ENTER YOUR COMMAND!")
            command = input()
            mode, filename = parse_command(command)
            ################## download mode ###################
            if mode == 'download':
                node.download(filename)
            #################### exit mode ####################
            elif mode == 'exit':
                node.exit_network()
                exit(0)
            #################### show mode ####################
            elif mode == 'show':
                print(self.fetch_owned_files())
            #################### getip mode ####################
            elif mode == 'getip':
                print(self.ip_addr)
            #################### help mode ####################
            elif mode == 'help':
                print("COMMAND AVAILABLE:")
                print("- download fileName: to download a fileName in the network.")
                print("- exit: to exit from the network.")
                print("- show: to show local file names available.")
                print("- getip: to show own ip address.")
            else:
                print("Error! Invalid command.")


if __name__ == '__main__':
    node = Node(request_port_TCP=generate_random_port(),
                download_port_TCP=generate_random_port())
    node.run()
