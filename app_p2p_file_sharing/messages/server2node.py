from messages.message import Message

class Server2Node(Message):
    def __init__(self, search_result: list):#, filename: str):

        super().__init__()
        self.search_result = search_result
