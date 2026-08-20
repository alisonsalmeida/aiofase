import asyncio

import pytest
import pytest_asyncio

from aiofase.server import Server


@pytest.fixture
def endpoints(tmp_path):
    sender_endpoint = f'ipc://{tmp_path}/sender'
    receiver_endpoint = f'ipc://{tmp_path}/receiver'
    return sender_endpoint, receiver_endpoint


@pytest_asyncio.fixture
async def broker(endpoints):
    sender_endpoint, receiver_endpoint = endpoints
    server = Server(sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint)
    task = asyncio.create_task(server.run())

    yield server

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    server.close()


async def run_service(service):
    """Start `service.run()` as a background task and return it."""
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.2)  # let SUB subscriptions propagate (ZMQ slow-joiner)
    return task


async def stop_service(task, service=None):
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    if service is not None:
        service.close()


async def wait_until(predicate, timeout=2.0, interval=0.02):
    """Poll `predicate()` until truthy or raise `AssertionError` on timeout."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        if predicate():
            return

        await asyncio.sleep(interval)

    raise AssertionError(f'condition not met within {timeout}s')
