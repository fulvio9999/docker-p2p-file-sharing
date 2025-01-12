from messages.message import Message
from configs import CFG, Config
config = Config.from_json(CFG)

class Node2Node(Message):
    def __init__(self, filename: str, mode=config.node_requests_mode.DOWNLOAD, size=-1, range=None, portUDP=None):

        super().__init__()
        self.mode = mode
        self.filename = filename
        self.size = size
        self.range = range
        self.portUDP = portUDP
