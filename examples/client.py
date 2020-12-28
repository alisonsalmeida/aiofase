from datetime import datetime
from asyncio import transports
from typing import Optional

import asyncio
import json


class AIOFaseClient(asyncio.Protocol):
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
            lambda: AIOFaseClient(self, on_connection_lost),
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
