import asyncio

import pytest

from aiofase import MicroService, security
from aiofase.server import Server

from .conftest import run_service, stop_service, wait_until


class Caller(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint, **kwargs):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
            enable_heartbeat=False, **kwargs)


class Worker(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint, **kwargs):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
            enable_heartbeat=False, **kwargs)

    @MicroService.action
    async def echo(self, service, data):
        return data


@pytest.fixture
def curve_keys(tmp_path):
    keys_dir = str(tmp_path / 'keys')
    server_public, server_secret = security.generate_keypair('broker', keys_dir)
    client_public, client_secret = security.generate_keypair('client', keys_dir)
    return {
        'server_public': server_public,
        'server_secret': server_secret,
        'client_public': client_public,
        'client_secret': client_secret,
    }


async def test_action_round_trip_over_curve_encrypted_channel(endpoints, curve_keys):
    sender_endpoint, receiver_endpoint = endpoints

    server = Server(
        sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
        curve_secretkey_file=curve_keys['server_secret'])
    server_task = asyncio.create_task(server.run())
    await asyncio.sleep(0.2)

    worker = Worker(
        sender_endpoint, receiver_endpoint,
        curve_secretkey_file=curve_keys['client_secret'], server_publickey_file=curve_keys['server_public'])
    worker_task = await run_service(worker)

    caller = Caller(
        sender_endpoint, receiver_endpoint,
        curve_secretkey_file=curve_keys['client_secret'], server_publickey_file=curve_keys['server_public'])
    caller_task = await run_service(caller)

    result = await asyncio.wait_for(caller.request_action('echo', {'secret': 'value'}), timeout=3)
    assert result == {'secret': 'value'}

    await stop_service(caller_task, caller)
    await stop_service(worker_task, worker)
    server_task.cancel()
    await asyncio.gather(server_task, return_exceptions=True)
    server.close()


async def test_client_without_curve_config_cannot_reach_curve_server(endpoints, curve_keys):
    """A plaintext client talking to a CURVE-only broker must not get a
    response: the CURVE handshake fails silently at the ZMTP level (this is
    inherent to ZMQ CURVE - it drops the connection rather than raising)."""
    sender_endpoint, receiver_endpoint = endpoints

    server = Server(
        sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
        curve_secretkey_file=curve_keys['server_secret'])
    server_task = asyncio.create_task(server.run())
    await asyncio.sleep(0.2)

    worker = Worker(
        sender_endpoint, receiver_endpoint,
        curve_secretkey_file=curve_keys['client_secret'], server_publickey_file=curve_keys['server_public'])
    worker_task = await run_service(worker)

    plaintext_caller = Caller(sender_endpoint, receiver_endpoint)  # no curve config at all
    caller_task = await run_service(plaintext_caller)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(plaintext_caller.request_action('echo', {'x': 1}, timeout=0.5), timeout=2)

    await stop_service(caller_task, plaintext_caller)
    await stop_service(worker_task, worker)
    server_task.cancel()
    await asyncio.gather(server_task, return_exceptions=True)
    server.close()
