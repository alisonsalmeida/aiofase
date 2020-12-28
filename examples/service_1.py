from client import Microservice
import asyncio


class Meter(Microservice):
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

    async def on_broadcast(self, service, client, data):
        print(f'service: {service}, data: {data}')

    @Microservice.action
    async def turnMeter(self, _service: str, data: dict):
        print(_service, data)
        await asyncio.sleep(100)

    @Microservice.task
    async def worker(self):
        import random
        while True:
            await self.request_action('save_database', {'voltage': random.randint(110, 135)})
            await asyncio.sleep(3)

    # @Microservice.task
    # def worker_2(self):
    #     while True:
    #         print('running task 2')
    #         sleep(1)
    #
    # @Microservice.task
    # def worker_3(self):
    #     while True:
    #         print('running task 3')
    #         sleep(5)


loop = asyncio.get_event_loop()
loop.run_until_complete(Meter().execute(True))
