from src.protocol import ServerProtocol, ClientProtocol

import asyncio
import json


class Connections(dict):
    def __init__(self, connections: dict):
        super().__init__()
        self._it = iter(connections)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = next(self._it)
        except StopIteration:
            raise StopAsyncIteration
        return value


class Server:
    def __init__(self, host: str, port: int):
        self.messages = list()
        self.connections = dict()
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.process_messages())

    async def on_service_connect(self, message: dict):
        client = message['client']
        self.connections[client]['object'].name_service = message['service']
        await self.send_broadcast(message, 'on_service_connect')

    async def on_service_disconnect(self, message: dict):
        await self.send_broadcast(message, 'on_service_disconnect')

    async def on_broadcast(self, message: dict):
        await self.send_broadcast(message, 'on_broadcast')

    async def on_request_action(self, message: dict):
        await self.send_broadcast(message, 'on_request_action')

    async def send_broadcast(self, message: dict, action: str):
        client = message['client']
        async for _client in Connections(self.connections):
            if _client != client:
                connection = self.connections[_client]
                await self._send_broadcast(connection, action, message)

    async def _send_broadcast(self, connection, action, message):
        transport = connection['connection']
        _message = json.dumps(message)
        transport.write(_message.encode())

    async def process_messages(self):
        while True:
            for idx, message in enumerate(self.messages):
                if 'action' in message and 'payload' in message:
                    action = message['action']

                    # events of broadcast
                    if hasattr(self, action):
                        func = getattr(self, action)
                        if callable(func):
                            self.loop.create_task(func(message))

                self.messages.pop(idx)
            await asyncio.sleep(0.01)

    async def execute(self):
        loop = asyncio.get_event_loop()
        server = await loop.create_server(
            lambda: ServerProtocol(self),
            self.host,
            self.port
        )

        await server.wait_closed()


class Microservice:
    def __init__(self, service, host='0.0.0.0', port=8888):
        self.service = service
        self.actions = dict()
        self.tasks = dict()
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.connected = False
        self._transport = None

        for name, func in self.service.__class__.__dict__.items():
            if callable(func) and 'action' in func.__name__:
                self.actions[name] = func

            if callable(func) and 'task' in func.__name__:
                self.tasks[name] = func

    @staticmethod
    def action(function):
        def _action_wrapper_(*args, **kwargs):
            return function(*args, **kwargs)

        return _action_wrapper_

    @staticmethod
    def task(function):
        def _task_wrapper_(*args, **kwargs):
            return function(*args, **kwargs)

        return _task_wrapper_

    async def on_connect(self):
        pass

    async def on_disconnect(self):
        pass

    async def on_service_connect(self, service, client, actions):
        pass

    async def on_service_disconnect(self, service):
        pass

    async def on_broadcast(self, service, client, payload):
        pass

    async def send_broadcast(self, data: dict):
        await self.send_message('on_broadcast', data)

    async def request_action(self, request, data):
        await self.send_message('on_request_action', data, request)

    async def send_message(self, action, data, request=None):
        message = dict()
        message['service'] = str(self.service)
        message['payload'] = data
        message['action'] = action

        if request is not None:
            message['request'] = request

        if self._transport:
            message = json.dumps(message)
            self._transport.write(message.encode())

    def __str__(self):
        return self.__class__.__name__

    async def execute(self, enable_task=False):
        if enable_task:
            for name, func in self.tasks.items():
                self.loop.run_in_executor(None, self.run_task, func)

        on_connection_lost = self.loop.create_future()
        transport, protocol = await self.loop.create_connection(
            lambda: ClientProtocol(self, on_connection_lost),
            self.host,
            self.port
        )

        try:
            self.transport = transport
            await on_connection_lost
        finally:
            transport.close()

    def run_task(self, func):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(func(self.service))

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, obj):
        self._transport = obj
