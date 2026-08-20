import asyncio
from argparse import ArgumentParser

import zmq
import zmq.asyncio as aiozmq
import zmq.auth
from zmq.auth.asyncio import AsyncioAuthenticator
import structlog
import logging

from . import security

logger = structlog.getLogger(__name__)


class Server:
    def __init__(self, sender_endpoint, receiver_endpoint, debug=False,
                 curve_secretkey_file=None, authorized_clients_dir=None):

        self.endpoints = (sender_endpoint, receiver_endpoint)
        self.context = aiozmq.Context()
        self.authenticator = None

        self.receiver = self.context.socket(zmq.PULL)
        self.sender = self.context.socket(zmq.PUB)

        # don't block on unsent messages if the socket/context is closed
        self.receiver.setsockopt(zmq.LINGER, 0)
        self.sender.setsockopt(zmq.LINGER, 0)

        self.curve_enabled = bool(curve_secretkey_file)
        self.authorized_clients_dir = authorized_clients_dir

        if curve_secretkey_file:
            public_key, secret_key = security.load_keypair(curve_secretkey_file)
            self.authenticator = AsyncioAuthenticator(self.context)

            for socket in (self.receiver, self.sender):
                socket.curve_secretkey = secret_key
                socket.curve_publickey = public_key
                socket.curve_server = True

        self.receiver.bind(receiver_endpoint)
        self.sender.bind(sender_endpoint)

        if debug:
            structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    def close(self):
        if self.authenticator is not None:
            self.authenticator.stop()

        self.receiver.close()
        self.sender.close()
        self.context.term()

    async def run(self):
        if self.curve_enabled:
            self.authenticator.start()

            if self.authorized_clients_dir:
                self.authenticator.configure_curve(domain='*', location=self.authorized_clients_dir)
            else:
                logger.warning(
                    'curve enabled without authorized_clients_dir: any client keypair will be '
                    'accepted (encryption only, no client authentication)')
                self.authenticator.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)

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

    parser.add_argument(
        '--curve-secretkey-file', action='store', dest='curve_secretkey_file', default=None,
        help='path to this server\'s .key_secret file, enables CURVE encryption')

    parser.add_argument(
        '--authorized-clients-dir', action='store', dest='authorized_clients_dir', default=None,
        help='directory of client .key public certificates allowed to connect (requires '
             '--curve-secretkey-file); if omitted, any client keypair is accepted')

    args = parser.parse_args()

    server = Server(
        sender_endpoint=args.sender_endpoint, receiver_endpoint=args.receiver_endpoint, debug=args.debug,
        curve_secretkey_file=args.curve_secretkey_file, authorized_clients_dir=args.authorized_clients_dir)

    asyncio.run(server.run())
