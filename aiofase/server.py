import asyncio
import zmq
import zmq.asyncio as aiozmq
import structlog
import logging


logger = structlog.getLogger(__name__)


class Server:
    def __init__(self, sender_endpoint, receiver_endpoint, debug=False):

        self.endpoints = (sender_endpoint, receiver_endpoint)
        self.context = aiozmq.Context()

        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.bind(receiver_endpoint)
        self.sender = self.context.socket(zmq.PUB)
        self.sender.bind(sender_endpoint)

        if debug:
            structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    async def run(self):
        logger.info(f'Server aiofase listening in: {self.endpoints[1]}')
        while True:
            data = await self.receiver.recv_string()
            logger.info(f'Server received: {data}')
            self.sender.send_string(data, zmq.NOBLOCK)


if __name__ == '__main__':
    server = Server(
        sender_endpoint='ipc:///tmp/sender', receiver_endpoint='ipc:///tmp/receiver', debug=True)

    asyncio.run(server.run())
