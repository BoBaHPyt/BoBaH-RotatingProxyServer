import asyncio
import typing
import traceback

from . import exceptions
from . import NewSocket


class ServerProtocol(asyncio.protocols.Protocol):
    __slots__ = ("_client_transport", "_endpoint_transport", "__client_sock", "__endpoint_sock",
                 "__handlers", "__options", "__handler")
    _client_transport: typing.Optional[asyncio.transports.Transport]
    _endpoint_transport: typing.Optional[asyncio.transports.Transport]
    __client_sock: NewSocket
    __endpoint_sock: NewSocket
    __handlers: list
    __options: dict
    __handler: int

    def __init__(self):
        self._client_transport = None
        self._endpoint_transport = None
        self.__client_sock = None
        self.__endpoint_sock = None
        self.__options = {"protocol": self}
        self.__handler = 0

    @classmethod
    def register_handler(cls, handler) -> None:
        if type(cls.__handlers) != list:
            cls.__handlers = []
        cls.__handlers.append(handler)
    
    @classmethod
    def remove_handler(cls, handler) -> None:
        if type(cls.__handlers) != list:
            cls.__handlers = []
        cls.__handlers.remove(handler)
    
    def _get_handler(self):
        if self.__handler < len(self.__handlers):
            return self.__handlers[self.__handler]
        return None
    
    async def _handle(self, from_transport, message=None, pair_transport=None):
        handler = self._get_handler()
        if handler:
            if handler.data_needed <= (message is not None):
                try:
                    next_handler = await handler.handle(from_transport, message, 
                                                                     pair_transport=pair_transport,
                                                                     options=self.__options)
                    if next_handler:
                        self.__handler += 1
                        await self._handle(from_transport, None, pair_transport)
                except exceptions.AuthNeeded:
                    pass
                except exceptions.ConnectionEndpoitFailed:
                    pass
                except exceptions.BadRequest:
                    pass
                except Exception as ex:
                    traceback.print_exc()
                    raise ex
            

    def connection_made(self, transport: asyncio.transports.Transport) -> None:
        if self._client_transport is None:
            self._client_transport = transport
            self.__client_sock = transport.get_extra_info("socket")._sock
            asyncio.ensure_future(self._handle(transport))
        else:
            self._endpoint_transport = transport
            self.__endpoint_sock = transport.get_extra_info("socket")._sock
            asyncio.ensure_future(self._handle(transport, None, self._client_transport))

    def connection_lost(self, exc) -> None:
        pass

    def eof_received(self) -> None:
        self._client_transport.close()
        if self._endpoint_transport:
            self._endpoint_transport.close()
        asyncio.ensure_future(self._handle(self._client_transport, b"", self._endpoint_transport))

    def pause_writing(self) -> None:
        pass

    def resume_writing(self) -> None:
        pass

    def data_received(self, data) -> None:
        from_transport = self._endpoint_transport
        to_transport = self._client_transport
        if self.__client_sock.recv_data_length > 0:
            from_transport = self._client_transport
            to_transport = self._endpoint_transport
            self.__client_sock.recv_data_length = 0
        asyncio.ensure_future(self._handle(from_transport, data, to_transport))
