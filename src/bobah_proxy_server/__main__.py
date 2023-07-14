if __name__ == "__main__":
    import asyncio
    import os

    from . import server
    from . import protocols
    from . import handlers


    async def main():
        host = os.getenv("HOST")
        port = int(os.getenv("PORT"))
        str_protocol = os.getenv("PROTOCOL") or "HTTP"
        backlog = int(os.getenv("BACKLOG"))
        proxy_list = os.getenv("PROXY_LIST") or "proxylist.json"
        user_list = os.getenv("USER_LIST") or "master:qwsaasxz"

        protocol = protocols.ServerProtocol

        client_conn_handler = handlers.HttpConnectionHandler() if str_protocol == "HTTP" else handlers.SocksConnectionHandler()
        protocol.register_handler(client_conn_handler)

        if user_list:
            auth_handler = handlers.AuthHandler(None)
            protocol.register_handler(auth_handler)
        
        endpoint_conn_handler = handlers.EndpointConnectionHandler(None)
        protocol.register_handler(endpoint_conn_handler)

        forwarding_handler = handlers.ForwardingHandler()
        protocol.register_handler(forwarding_handler)
        
        close_handler = handlers.CloseHandler()
        protocol.register_handler(close_handler)

        proxy_server = server.ProxyServer(host, port, protocol, backlog)

        await proxy_server.run_forever()
    

    asyncio.run(main())
