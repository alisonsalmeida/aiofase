from asyncio import transports
from typing import Optional
from datetime import datetime

import asyncio
import json
import hashlib


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


class AIOFaseServer:
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
            lambda: AIOFaseProtocol(self),
            self.host,
            self.port
        )

        await server.wait_closed()


class AIOFaseProtocol(asyncio.Protocol):
    def __init__(self, aiofase: AIOFaseServer):
        self.aiofase = aiofase
        self._transport = None
        self.name = str()
        self.name_service = str()
        self.actions = list()
        self.loop = asyncio.get_event_loop()

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.transport = transport
        now = datetime.utcnow().isoformat().__str__()
        self.name = hashlib.md5(now.encode()).hexdigest()
        self.aiofase.connections[self.name] = dict()
        self.aiofase.connections[self.name]['name'] = self.name
        self.aiofase.connections[self.name]['connection'] = self.transport
        self.aiofase.connections[self.name]['object'] = self

    def connection_lost(self, exc: Optional[Exception]) -> None:
        del self.aiofase.connections[self.name]
        message = {
            'service': self.name_service,
            'action': 'on_service_disconnect',
            'client': self.name,
            'payload': {}
        }

        self.aiofase.messages.append(message)

    def data_received(self, data: bytes) -> None:
        data = data.decode()

        try:
            data = json.loads(data)
            data['client'] = self.name
            print(f'data: {data}')
            self.aiofase.messages.append(data)

        except json.JSONDecodeError as e:
            pass

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, obj: transports.BaseTransport):
        self._transport = obj

