"""configs in json format"""
import json
import socket

CFG = {
    "directory": {
        "logs_dir": "logs/",
        "node_files_dir": "node_files/",
    },
    "constants": {
        "AVAILABLE_PORTS_RANGE": (1024, 65535), # range of available ports on the local computer
        "SERVER_ADDR": ('172.20.0.2', 12345),
        "TCP_BUFFER_SIZE": 8192,
        "UDP_BUFFER_SIZE": 8192,#9216,
        "CHUNK_PIECES_SIZE": 8192 - 2000,#9216 - 2000,
        "NODE_TIME_INTERVAL": 10,        # the interval time that each node periodically informs the server (in seconds)
        "SERVER_TIME_INTERVAL": 10      #the interval time that the server periodically checks which nodes are connected (in seconds)
    },
    "server_requests_mode": {
        "REGISTER": 0,  # tells the server that it is in the network
        "EXIT": 1       # tells the server that it left the network
    },
    "node_requests_mode": {
        "SIZE": 0,      # tells request of file size
        "CHUNKS": 1,    # tells request of download file in chunks
        "DOWNLOAD": 2   # tells request of download total file
    }
}


class Config:
    """Config class which contains directories, constants, etc."""

    def __init__(self, directory, constants, node_requests_mode, server_requests_mode):
        self.directory = directory
        self.constants = constants
        self.server_requests_mode = server_requests_mode
        self.node_requests_mode = node_requests_mode

    @classmethod
    def from_json(cls, cfg):
        """Creates config from json"""
        params = json.loads(json.dumps(cfg), object_hook=HelperObject)
        return cls(params.directory, params.constants, params.node_requests_mode, params.server_requests_mode)


class HelperObject(object):
    """Helper class to convert json into Python object"""
    def __init__(self, dict_):
        self.__dict__.update(dict_)