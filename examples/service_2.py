from client import Microservice
import asyncio
from time import sleep


class Database(Microservice):
    def __init__(self):
        super().__init__(self)

    async def on_connect(self):
        print('conectado')

    async def on_disconnect(self):
        print('desconectado')

    async def on_service_connect(self, service, client, actions):
        print(f'novo servico: {service}, actions: {actions}')

    async def on_service_disconnect(self, service):
        print(f'servico desconectado: {service}')

    async def on_broadcast(self, service, client, payload):
        print(f'service: {service}, data: {payload}')

    @Microservice.action
    async def save_database(self, service: str, client: str, payload: dict):
        print(f'saving the data: {payload}')

    @Microservice.task
    async def worker(self):
        import random
        while True:
            await self.send_broadcast({'voltage': random.randint(110, 135)})
            await asyncio.sleep(3)


loop = asyncio.get_event_loop()
loop.run_until_complete(Database().execute(True))
