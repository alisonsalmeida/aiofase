from asyncio import transports
from datetime import datetime
from typing import Optional

import asyncio
import hashlib
import json


class ServerProtocol(asyncio.Protocol):
    def __init__(self, aiofase):
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


class ClientProtocol(asyncio.Protocol):
    def __init__(self, service, on_connection_lost):
        self.service = service
        self.on_connection_lost = on_connection_lost
        self._transport = None
        self.loop = asyncio.get_event_loop()

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.transport = transport
        # call callback to on connect
        self.loop.create_task(
            asyncio.wait_for(
                self.service.on_connect(),
                timeout=0.5
            )
        )

        # send to server message to broadcast new service
        message = {
            'service': str(self.service),
            'action': 'on_service_connect',
            'payload': {},
            'actions': [action for action in self.service.actions.keys()]
        }
        message = json.dumps(message)
        self.transport.write(message.encode())

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.on_connection_lost.set_result(True)
        self.loop.create_task(
            asyncio.wait_for(
                self.service.on_disconnect(),
                timeout=0.5
            )
        )

    def data_received(self, data: bytes) -> None:
        data = data.decode()
        data = json.loads(data)

        action = data['action']
        action_private = f'_{action}'

        if hasattr(self, action_private):
            func = getattr(self, action_private)
            if callable(func):
                self.loop.create_task(func(action, **data))

    async def _on_service_connect(self, _action, **kwargs):
        func = getattr(self.service, _action)
        print('novo service')
        future = asyncio.wait_for(func(
            kwargs['service'],
            kwargs['client'],
            kwargs['actions']
            ),
            timeout=0.2)
        await self.create_future(future)

    async def _on_service_disconnect(self, _action, **kwargs):
        func = getattr(self.service, _action)
        future = asyncio.wait_for(func(kwargs['service']), timeout=0.2)
        await self.create_future(future)

    async def _on_broadcast(self, _action, **kwargs):
        func = getattr(self.service, _action)
        future = asyncio.wait_for(func(
            kwargs['service'],
            kwargs['client'],
            kwargs['payload']
        ),
            timeout=0.2)
        await self.create_future(future)

    async def _on_request_action(self, _action, **kwargs):
        action = kwargs['request']
        if action in self.service.actions:
            func = self.service.actions[action]
            future = asyncio.wait_for(func(
                self.service,
                kwargs['service'],
                kwargs['client'],
                kwargs['payload']
            ),
                timeout=0.2)
            await self.create_future(future)

    async def create_future(self, future):
        self.loop.create_task(future)

    @property
    def transport(self):
        return self._transport

    @transport.setter
    def transport(self, obj):
        self._transport = obj
