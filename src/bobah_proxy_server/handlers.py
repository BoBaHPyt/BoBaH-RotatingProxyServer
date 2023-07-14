import asyncio
import typing
import base64

from . import exceptions


class BaseHandler:
    __slots__ = ("data_needed", )
    data_needed: bool

    def __init__(self):
        self.data_needed = False

    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, options={}, *args, **kwargs) -> bool:
        pass


class ClientConnectionHandler(BaseHandler):
    def __init__(self):
        self.data_needed = True


class HttpConnectionHandler(ClientConnectionHandler):
    def parse_first_row(self, row, result):
        result["data"] = row + b"/r/n"

        split_row = row.split(b" ")
        if len(split_row) != 3:
            raise exceptions.BadRequest()
        method, addr, version = split_row
        result["method"] = method

        if b"://" in addr:
            addr = addr.split(b"://", 1)[1]
        hp_addr = addr.split(b":")
        if len(hp_addr) == 1:
            host = hp_addr[0]
            port = 80
            result["addr"] = {"host": host.decode(), "port": port}
        elif len(hp_addr) == 2 and hp_addr[1].isdigit():
            host = hp_addr[0]
            port = hp_addr[1]
            result["addr"] = {"host": host.decode(), "port": int(port.decode())}
        else:
            raise exceptions.BadRequest()
        
        return result

    def parse_row(self, row, result):
        if row:
            k, v = row.split(b":", 1)
            while v[0] == 32:
                v = v[1:]
            if k.lower() != b"proxy-authorization":
                result["data"] += row + b"\r\n"
            else:
                auth = v.split(b" ", 1)[1]
                auth = base64.b64decode(auth).decode()
                username, password = auth.split(":", 1)
                result["auth"] = {"username": username, "password": password}
            result["headers"][k.decode()] = v.decode()
        else:
            if b"\r\n\r\n" not in result["data"]:
                result["data"] += b"\r\n"

    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, options={}, *args, **kwargs) -> bool:
        print(f"New input connection {from_transport.get_extra_info('peername')}")

        result = {"headers": {}}

        rows = message.split(b"\r\n")
        self.parse_first_row(rows.pop(0), result)
        for row in rows:
            self.parse_row(row, result)
        options["request"] = result
        return True


class SocksConnectionHandler(ClientConnectionHandler):
    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, options={}, *args, **kwargs) -> bool:
        pass


class AuthHandler(BaseHandler):
    __slots__ = ("data_needed", "_user_manager", )

    def __init__(self, user_manager):
        self.data_needed = False
        self._user_manager = user_manager

    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, options={}, *args, **kwargs) -> bool:
        print("auth ok")
        return True


class EndpointConnectionHandler(BaseHandler):
    __slots__ = ("data_needed", "_proxy_manager", )

    def __init__(self, proxy_manager):
        self.data_needed = False
        self._proxy_manager = proxy_manager

    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, pair_transport: asyncio.transports.Transport,
                           options={}, *args, **kwargs) -> bool:
        status = options.get("endpoint_connection_status", 0)
        if status == 0:
            ioloop = asyncio.get_event_loop()
            protocol = lambda: options["protocol"]
            host = options["request"]["addr"]["host"]
            port = options["request"]["addr"]["port"]
            options["endpoint_connection_status"] = 1
            await ioloop.create_connection(protocol, host, port)
            return False
        if status == 1:
            if options["request"]["method"] != b"CONNECT":
                from_transport.write(options["request"]["data"])
            else:
                pair_transport.write(b"HTTP/1.1 200 Connection established\r\nProxy-agent: BoBaHProxy\r\n\r\n")
            options["endpoint_connection_status"] = 2
            return True


class ForwardingHandler(BaseHandler):
    def __init__(self):
        self.data_needed = True

    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, pair_transport: asyncio.transports.Transport, 
                           options={}, *args, **kwargs) -> bool:
        pair_transport.write(message)
        if not message:
            return True


class CloseHandler(BaseHandler):
    def __init__(self):
        self.data_needed = False
    
    async def handle(self, from_transport: asyncio.transports.Transport,
                           message: bytes, pair_transport: asyncio.transports.Transport, 
                           options={}, *args, **kwargs) -> [bool, typing.Optional[dict]]:
        user = options.get("user")
        if user is not None:
            user.release_thread()
        return True
