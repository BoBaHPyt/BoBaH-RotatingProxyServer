version = "0.0.dev"
proxy_agent = f"BoBaHProxy {version}"

import socket


class NewSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.recv_data_length = 0
    
    def recv(self, *args, **kwargs):
        data = super().recv(*args, **kwargs)
        if data:
            self.recv_data_length += len(data)
        return data


socket.socket = NewSocket


from . import exceptions
from . import handlers
from . import protocols

__all__ = (
    "exceptions",
    "handlers",
    "protocols"
)
