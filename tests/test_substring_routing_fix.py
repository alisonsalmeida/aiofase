import asyncio

from aiofase import MicroService

from .conftest import run_service, stop_service


class Caller(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        self.responses = []
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)

    async def on_response(self, service, data):
        self.responses.append((service, data))


class ServiceB(MicroService):
    """Name matters: the payload data below embeds the literal substring
    'ServiceB:' so this class must be named ServiceB to reproduce the bug."""

    def __init__(self, sender_endpoint, receiver_endpoint):
        self.invocations = []
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)

    @MicroService.action
    async def some_action(self, service, data):
        self.invocations.append(data)
        return {'ok': True}


async def test_action_dispatch_not_hijacked_by_embedded_service_name(broker, endpoints):
    """Regression test: dispatch must match frame prefixes exactly, not any
    substring anywhere in the package. Previously `f'{self.name}:' in package`
    matched even when the service name only appeared inside the JSON body,
    silently swallowing a legitimate action call into on_response instead of
    invoking the actual @action handler.
    """
    sender_endpoint, receiver_endpoint = endpoints

    caller = Caller(sender_endpoint, receiver_endpoint)
    caller_task = await run_service(caller)

    service_b = ServiceB(sender_endpoint, receiver_endpoint)
    service_b_task = await run_service(service_b)

    # the data payload embeds the exact substring 'ServiceB:' that used to
    # false-positive match the `f'{self.name}:' in package` check
    result = await asyncio.wait_for(
        caller.request_action('some_action', {'note': 'ServiceB:xyz'}), timeout=2)

    assert result == {'ok': True}
    assert service_b.invocations == [{'note': 'ServiceB:xyz'}]
    assert caller.responses == []  # must NOT have been misrouted to on_response

    await stop_service(service_b_task, service_b)
    await stop_service(caller_task, caller)
