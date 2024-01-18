import zmq.asyncio as aiozmq
import zmq
import json
import asyncio


class MicroService:
    def __init__(self, service, sender_endpoint, receiver_endpoint, serializer=None, debug=False) -> None:
        self.name = service.__class__.__name__
        self.sender_endpoint = sender_endpoint
        self.receiver_endpoint = receiver_endpoint
        self.serializer = serializer or json
        self.debug = debug
        self.actions = dict()
        self.tasks = dict()

        self.context = aiozmq.Context()

        self.sender = self.context.socket(zmq.PUSH)
        self.sender.connect(receiver_endpoint)
        
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(sender_endpoint)

        self.receiver.setsockopt_string(zmq.SUBSCRIBE, '')

        for name, func in service.__class__.__dict__.items():
            if callable(func):
                if 'action_wrapper' in func.__name__:
                    self.actions[name] = func
                    self.receiver.setsockopt_string(zmq.SUBSCRIBE, f'{name}:')

                elif 'task_wrapper' in func.__name__:
                    self.tasks[name] = func

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
        pass

    async def on_new_service(self, service: str, actions: list[str]):
        pass

    async def on_broadcast(self, service: str, data: dict):
        pass

    async def on_response(self, service: str, data: dict):
        pass

    async def send_broadcast(self, data):
        self.sender.send_string('<b>:%s' % self.serializer.dumps({'s': self.name, 'd': data}), zmq.NOBLOCK)

    async def request_action(self, action, data):
        self.sender.send_string('%s:%s' % (action, self.serializer.dumps({'s': self.name, 'd': data})), zmq.NOBLOCK)

    async def response(self, service, data):
        self.sender.send_string('%s:%s' % (service, self.serializer.dumps({'s': self.name, 'd': data})), zmq.NOBLOCK)

    async def run(self, enable_tasks=True):
        self.sender.send_string('<r>:%s' % self.serializer.dumps({'s': self.name,
                                                      'a': [action for action in self.actions]}), zmq.NOBLOCK)
        
        if enable_tasks:
            # initialize tasks
            for name, func in self.tasks.items():
                asyncio.create_task(func(self), name=name)

        while True:
            package = await self.receiver.recv_string()

            if '<r>:' in package:
                payload = self.serializer.loads(package[4:])
                service = payload['s']
                actions = payload['a']
                
                if self.name == service:
                    asyncio.create_task(self.on_connect())

                else:
                    asyncio.create_task(self.on_new_service(service, actions))

            elif '<b>:' in package:
                payload = self.serializer.loads(package[4:])
                service = payload['s']
                data = payload['d']
                
                if self.name != service:
                    asyncio.create_task(self.on_broadcast(service, data))

            elif f'{self.name}:' in package:
                pos = package.find(':')
                payload = self.serializer.loads(package[pos + 1:])
                service = payload['s']
                data = payload['d']

                asyncio.create_task(self.on_response(service, data))

            else:
                pos = package.find(':')
                payload = self.serializer.loads(package[pos + 1:])
                action = package[:pos]
                service = payload['s']
                data = payload['d']

                if action in self.actions:
                    func = self.actions[action]
                    asyncio.create_task(func(self, service, data))


if __name__ == '__main__':
    microservice = MicroService(sender='ipc:///tmp/sender', receiver='ipc:///tmp/receiver')
    asyncio.run(microservice.run())
