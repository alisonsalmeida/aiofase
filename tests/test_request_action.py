import asyncio

from aiofase import MicroService

from .conftest import run_service, stop_service, wait_until


class Caller(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)


class Worker(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)

    @MicroService.action
    async def save_data(self, service, data):
        return {'saved': data}

    @MicroService.action
    async def fail(self, service, data):
        raise ValueError(f'invalid data: {data}')

    @MicroService.action
    async def slow(self, service, data):
        await asyncio.sleep(2)
        return {'too': 'slow'}


async def test_request_action_success(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    caller = Caller(sender_endpoint, receiver_endpoint)
    caller_task = await run_service(caller)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    result = await asyncio.wait_for(caller.request_action('save_data', {'sensor': 42}), timeout=2)

    assert result == {'saved': {'sensor': 42}}
    assert caller.requests == {}

    await stop_service(worker_task, worker)
    await stop_service(caller_task, caller)


async def test_request_action_propagates_remote_exception(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    caller = Caller(sender_endpoint, receiver_endpoint)
    caller_task = await run_service(caller)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    try:
        await asyncio.wait_for(caller.request_action('fail', {'sensor': 42}), timeout=2)
        assert False, 'expected ValueError'
    except ValueError as e:
        assert 'invalid data' in str(e)

    assert caller.requests == {}

    await stop_service(worker_task, worker)
    await stop_service(caller_task, caller)


async def test_request_action_times_out(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    caller = Caller(sender_endpoint, receiver_endpoint)
    caller_task = await run_service(caller)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    try:
        await asyncio.wait_for(caller.request_action('slow', {}, timeout=0.3), timeout=2)
        assert False, 'expected asyncio.TimeoutError'
    except asyncio.TimeoutError:
        pass

    # no leaked entry in the pending-requests table after the timeout fires
    await wait_until(lambda: caller.requests == {})

    await stop_service(worker_task, worker)
    await stop_service(caller_task, caller)
