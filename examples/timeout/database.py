from aiofase.microservice import MicroService

import structlog
import asyncio


logger = structlog.getLogger(__name__)


class Database(MicroService):
    def __init__(self):
        super().__init__(self, sender_endpoint='tcp://0.0.0.0:3000', receiver_endpoint='tcp://0.0.0.0:4000')

    async def on_connect(self):
        logger.info('### on_connect ###')
        await self.send_broadcast({'message': 'database service is online'})

    async def on_new_service(self, service, actions):
        logger.info(f'### on_new_service ### service: {service} - actions: {actions}')

    @MicroService.action
    async def save_data(self, service, data):
        logger.info(f'### action::save_data: {data}')
        return {'save_data_ack': {'status': 'saved'}}

    @MicroService.action
    async def wait_save_data(self, service, data):
        logger.info(f'### action::wait_save_data: {data}')
        await asyncio.sleep(5)

        return {'wait_save_data_ack': {'status': 'saved'}}

    @MicroService.action
    async def error_save_data(self, service, data):
        logger.info(f'### action::error_save_data: {data}')
        raise ValueError(f'invalid data: {data}')

    @MicroService.action
    async def timeout_save_data(self, service, data):
        logger.info(f'### action::timeout_save_data: {data}')
        await asyncio.sleep(7)
        return {'timeout_save_data_ack': {'status': 'saved'}}


if __name__ == '__main__':
    database = Database()
    asyncio.run(database.run())
