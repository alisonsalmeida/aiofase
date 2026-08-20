import asyncio
from argparse import ArgumentParser

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
        self.sender = self.context.socket(zmq.PUB)

        # don't block on unsent messages if the socket/context is closed
        self.receiver.setsockopt(zmq.LINGER, 0)
        self.sender.setsockopt(zmq.LINGER, 0)

        self.receiver.bind(receiver_endpoint)
        self.sender.bind(sender_endpoint)

        if debug:
            structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    def close(self):
        self.receiver.close()
        self.sender.close()
        self.context.term()

    async def run(self):
        logger.info(f'Server aiofase listening in: {self.endpoints[1]}')
        while True:
            data = await self.receiver.recv_string()
            logger.debug(f'Server received: {data}')
            self.sender.send_string(data, zmq.NOBLOCK)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-sender', '--sender-endpoint', action='store', dest='sender_endpoint', default='tcp://0.0.0.0:3000')

    parser.add_argument(
        '-receiver', '--receiver-endpoint', action='store', dest='receiver_endpoint', default='tcp://0.0.0.0:4000')

    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False)

    args = parser.parse_args()

    server = Server(
        sender_endpoint=args.sender_endpoint, receiver_endpoint=args.receiver_endpoint, debug=args.debug)

    asyncio.run(server.run())
