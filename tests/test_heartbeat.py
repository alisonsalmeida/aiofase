import asyncio

from aiofase import MicroService

from .conftest import run_service, stop_service, wait_until

HEARTBEAT_INTERVAL = 0.15
HEARTBEAT_TIMEOUT = 0.4


class Watcher(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        self.disconnected = []
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
            enable_heartbeat=True, heartbeat_interval=HEARTBEAT_INTERVAL, heartbeat_timeout=HEARTBEAT_TIMEOUT)

    async def on_service_disconnect(self, service):
        self.disconnected.append(service)


class Flaky(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint,
            enable_heartbeat=True, heartbeat_interval=HEARTBEAT_INTERVAL, heartbeat_timeout=HEARTBEAT_TIMEOUT)


async def test_on_service_disconnect_fires_after_heartbeat_timeout(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    watcher = Watcher(sender_endpoint, receiver_endpoint)
    watcher_task = await run_service(watcher)

    flaky = Flaky(sender_endpoint, receiver_endpoint)
    flaky_task = await run_service(flaky)

    # let at least one heartbeat go through so Watcher knows Flaky is alive
    await wait_until(lambda: 'Flaky' in watcher.known_services)

    # simulate Flaky vanishing without a graceful shutdown: stop its run loop
    # (which also stops its heartbeat-sender task, since run() gathers them together)
    await stop_service(flaky_task, flaky)

    await wait_until(lambda: watcher.disconnected == ['Flaky'], timeout=2.0)
    assert 'Flaky' not in watcher.known_services

    await stop_service(watcher_task, watcher)


async def test_active_service_is_not_marked_disconnected(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    watcher = Watcher(sender_endpoint, receiver_endpoint)
    watcher_task = await run_service(watcher)

    alive = Flaky(sender_endpoint, receiver_endpoint)
    alive_task = await run_service(alive)

    await wait_until(lambda: 'Flaky' in watcher.known_services)

    # stay up through more than one heartbeat_timeout window
    await asyncio.sleep(HEARTBEAT_TIMEOUT * 2)

    assert watcher.disconnected == []
    assert 'Flaky' in watcher.known_services

    await stop_service(alive_task, alive)
    await stop_service(watcher_task, watcher)
