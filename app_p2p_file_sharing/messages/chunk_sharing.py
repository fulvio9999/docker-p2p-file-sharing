from messages.message import Message

class ChunkSharing(Message):
    def __init__(self, filename: str, range: tuple, idx: int =-1, chunk: bytes = None):

        super().__init__()
        self.filename = filename
        self.range = range
        self.idx = idx
        self.chunk = chunk
