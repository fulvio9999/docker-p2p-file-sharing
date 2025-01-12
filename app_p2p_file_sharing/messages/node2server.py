from messages.message import Message

class Node2Server(Message):
    def __init__(self, mode: int, request_port_TCP: int, download_port_TCP: int):#, filename: str):

        super().__init__()
        self.mode = mode
        self.request_port_TCP = request_port_TCP
        self.download_port_TCP = download_port_TCP
