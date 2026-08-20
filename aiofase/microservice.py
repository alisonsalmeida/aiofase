from typing import Dict, Any

import zmq.asyncio as aiozmq
import zmq
import json
import structlog
import logging
import asyncio
import inspect
import uuid
import builtins

logger = structlog.getLogger(__name__)


class MicroService:
    def __init__(self, service, sender_endpoint, receiver_endpoint, serializer=None, debug=False,
                 enable_heartbeat=True, heartbeat_interval=5, heartbeat_timeout=None):
        if debug:
            structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

        self.name = service.__class__.__name__
        self.sender_endpoint = sender_endpoint
        self.receiver_endpoint = receiver_endpoint
        self.serializer = serializer or json
        self.actions = dict()
        self.tasks = dict()

        self.enable_heartbeat = enable_heartbeat
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout or (heartbeat_interval * 3)
        self.known_services: Dict[str, float] = {}

        self.context = aiozmq.Context()

        self.sender = self.context.socket(zmq.PUSH)
        self.receiver = self.context.socket(zmq.SUB)

        # don't block on unsent messages if the socket/context is closed
        self.sender.setsockopt(zmq.LINGER, 0)
        self.receiver.setsockopt(zmq.LINGER, 0)

        self.sender.connect(receiver_endpoint)
        self.receiver.connect(sender_endpoint)

        self.receiver.setsockopt_string(zmq.SUBSCRIBE, '')
        self.requests: Dict[str, asyncio.Future] = {}

        for name, func in inspect.getmembers(service.__class__, predicate=callable):
            if 'action_wrapper' in getattr(func, '__name__', ''):
                self.actions[name] = func
                self.receiver.setsockopt_string(zmq.SUBSCRIBE, f'{name}:')

            elif 'task_wrapper' in getattr(func, '__name__', ''):
                self.tasks[name] = func

        logger.info(f'Load tasks: {[task for task in self.tasks]}')
        logger.info(f'Load actions: {[action for action in self.actions]}')

    def close(self):
        self.sender.close()
        self.receiver.close()
        self.context.term()

    @staticmethod
    def action(function: callable):
        async def action_wrapper(*args, **kwargs):
            return await function(*args, **kwargs)

        return action_wrapper

    @staticmethod
    def task(function: callable):
        async def task_wrapper(*args, **kwargs):
            return await function(*args, **kwargs)

        return task_wrapper

    async def on_connect(self):
        logger.info('connect on broker')

    async def on_new_service(self, service: str, actions: list[str]):
        logger.info('new service connect on broker')

    async def on_service_disconnect(self, service: str):
        logger.info(f'service disconnected (no heartbeat): {service}')

    async def on_broadcast(self, service: str, data: dict):
        logger.info('new message on broadcast')

    async def on_response(self, service: str, data: dict):
        logger.info(f'new response the service: {service}')

    def _touch(self, service: str):
        if service == self.name:
            return

        self.known_services[service] = asyncio.get_event_loop().time()

    async def send_broadcast(self, data):
        payload = self.serializer.dumps({'s': self.name, 'd': data})
        self.sender.send_string(f'<b>:{payload}', zmq.NOBLOCK)

    def request_action(self, action, data, timeout=None):
        request_id = uuid.uuid4().hex
        payload = self.serializer.dumps({'s': self.name, 'd': data, 'areq': {'i': request_id, 'timeout': timeout}})
        result = asyncio.Future()
        self.requests[request_id] = {'result': result, 'task_timeout': None}

        self.sender.send_string(f'{action}:{payload}', zmq.NOBLOCK)

        if timeout is not None:
            task_timeout = asyncio.create_task(self._result_timeout(request_id, result, timeout))
            self.requests[request_id]['task_timeout'] = task_timeout

        return result

    async def _result_timeout(self, request_id: str, future: asyncio.Future, timeout: int):
        await asyncio.sleep(timeout)
        self.requests.pop(request_id, None)
        if not future.done():
            future.set_exception(asyncio.TimeoutError)

    async def response(self, service, data):
        payload = self.serializer.dumps({'s': self.name, 'd': data})
        self.sender.send_string(f'{service}:{payload}', zmq.NOBLOCK)

    async def _response_action(self, service: str, request_id: str, data: Any, error: dict):
        entry = self.requests.pop(request_id, None)
        if entry is None:
            return

        future = entry['result']
        task_timeout = entry['task_timeout']

        if future.done():
            return

        if task_timeout is not None:
            task_timeout.cancel()

        if bool(error):
            cls = getattr(builtins, error['type'], Exception)
            future.set_exception(cls(error['error']))
            return

        future.set_result(data)


    async def _request_action(self, request_id: str, timeout, func: callable, service: str, data: dict):
        error = {}
        result = None

        try:
            if timeout is not None:
                result = await asyncio.wait_for(func(self, service, data), timeout)

            else:
                result = await func(self, service, data)

        except Exception as e:
            logger.error(f'error in process action: {e}')
            error = {'type': e.__class__.__name__, 'error': str(e)}

        finally:
            payload = self.serializer.dumps({'s': self.name, 'd': result, 'ares': {'i': request_id, 'error': error}})
            self.sender.send_string(f'<ares>:{payload}', zmq.NOBLOCK)

    async def _send_heartbeat(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            payload = self.serializer.dumps({'s': self.name})
            self.sender.send_string(f'<hb>:{payload}', zmq.NOBLOCK)

    async def _check_heartbeats(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            now = asyncio.get_event_loop().time()

            for service, last_seen in list(self.known_services.items()):
                if now - last_seen > self.heartbeat_timeout:
                    self.known_services.pop(service, None)
                    asyncio.create_task(self.on_service_disconnect(service))

    async def run(self, enable_tasks=True):
        actions = [action for action in self.actions]
        payload = self.serializer.dumps({'s': self.name, 'a': actions})
        self.sender.send_string(f'<r>:{payload}', zmq.NOBLOCK)

        if enable_tasks:
            # initialize tasks
            for name, func in self.tasks.items():
                logger.info(f'Starting task: {name}')
                asyncio.create_task(func(self), name=name)

        coroutines = [self._receive_loop()]

        if self.enable_heartbeat:
            coroutines.append(self._send_heartbeat())
            coroutines.append(self._check_heartbeats())

        # gathered (not create_task'd) so cancelling run() also stops these
        await asyncio.gather(*coroutines)

    async def _receive_loop(self):
        while True:
            try:
                package = await self.receiver.recv_string()

                if package.startswith('<r>:'):
                    payload = self.serializer.loads(package[4:])
                    service = payload['s']
                    actions = payload['a']

                    self._touch(service)

                    if self.name == service:
                        asyncio.create_task(self.on_connect())

                    else:
                        asyncio.create_task(self.on_new_service(service, actions))

                elif package.startswith('<b>:'):
                    payload = self.serializer.loads(package[4:])
                    service = payload['s']
                    data = payload['d']

                    self._touch(service)

                    if self.name != service:
                        asyncio.create_task(self.on_broadcast(service, data))

                elif package.startswith('<hb>:'):
                    payload = self.serializer.loads(package[5:])
                    service = payload['s']

                    self._touch(service)

                # this response from async future
                elif package.startswith('<ares>:'):
                    payload = self.serializer.loads(package[7:])
                    service = payload['s']
                    data = payload['d']
                    ares = payload['ares']

                    self._touch(service)

                    if service != self.name:
                        request_id = ares['i']
                        error = ares['error']
                        asyncio.create_task(self._response_action(service, request_id, data, error))

                elif package.startswith(f'{self.name}:'):
                    pos = package.find(':')
                    payload = self.serializer.loads(package[pos + 1:])
                    service = payload['s']
                    data = payload['d']

                    self._touch(service)

                    asyncio.create_task(self.on_response(service, data))

                else:
                    pos = package.find(':')
                    payload = self.serializer.loads(package[pos + 1:])
                    action = package[:pos]
                    service = payload['s']
                    data = payload['d']
                    areq = payload.get('areq', None)

                    self._touch(service)

                    if action in self.actions:
                        func = self.actions[action]

                        # async call
                        if areq is not None:
                            request_id = areq['i']
                            timeout = areq['timeout']

                            asyncio.create_task(self._request_action(request_id, timeout, func, service, data))
                            continue

                        asyncio.create_task(func(self, service, data))

            except Exception as e:
                logger.error(f'Fail to decode message: {e}')


if __name__ == '__main__':
    microservice = MicroService(sender='ipc:///tmp/sender', receiver='ipc:///tmp/receiver')
    asyncio.run(microservice.run())
