from aiofase.microservice import MicroService

import structlog
import asyncio
import random


logger = structlog.getLogger(__name__)


class EnergySensor(MicroService):
    def __init__(self) -> None:
        super().__init__(self, sender_endpoint='tcp://0.0.0.0:3000', receiver_endpoint='tcp://0.0.0.0:4000')

    async def on_connect(self):
        logger.info('### on_connect ###')

    async def on_new_service(self, service, actions):
        logger.info(f'### on_new_service ### service: {service} - actions: {actions}')

    async def on_response(self, service, data):
        logger.info(f'### on_response ### service: {service} respond an status of the action save_data previous resquested: {data}')

    @MicroService.task
    async def meter_process(self):
        logger.info('send message and not wait response')

        while True:
            sensor_data = random.randrange(10, 50, 1)
            self.request_action('save_data', {'sensor': sensor_data})
            await asyncio.sleep(2)

    @MicroService.task
    async def wait_meter_process(self):
        logger.info('send message and wait response, if timeout is not None, exception will be raised')

        while True:
            sensor_data = random.randrange(10, 50, 1)
            result = await self.request_action('wait_save_data', {'sensor': sensor_data}, timeout=10)
            logger.info(f'result for wait_save_data: {result}')
            await asyncio.sleep(2)

    @MicroService.task
    async def error_meter_process(self):
        logger.info('send message and capture exception in remote execution')

        while True:
            sensor_data = random.randrange(10, 50, 1)
            
            try:
                result = await self.request_action('error_save_data', {'sensor': sensor_data})
                logger.info(f'result for error_save_data, never execute here: {result}')

            except Exception as e:
                logger.error(f'error for remote execution in error_save_data: {e}')

            finally:
                await asyncio.sleep(2)

    @MicroService.task
    async def timeout_meter_process(self):
        logger.info('send message and capture timeout exception in remote execution')

        while True:
            sensor_data = random.randrange(10, 50, 1)
            
            try:
                # timeout value is less que time execution of the timeout_save_data
                result = await self.request_action('timeout_save_data', {'sensor': sensor_data}, timeout=3)
                logger.info(f'result for timeout_save_data, never execute here: {result}')

            except asyncio.TimeoutError as e:
                logger.error(f'timeout error for remote execution in error_save_data: {e}')

            finally:
                await asyncio.sleep(2)


if __name__ == '__main__':
    sensor = EnergySensor()
    asyncio.run(sensor.run())
