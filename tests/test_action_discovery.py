import asyncio

from aiofase import MicroService

from .conftest import run_service, stop_service


class ActionMixin:
    """A base class that defines an @action without inheriting from
    MicroService directly - the concrete service class below only inherits
    it, it never redefines `greet` in its own __dict__."""

    @MicroService.action
    async def greet(self, service, data):
        return {'greeting': 'hi'}


class GreeterService(ActionMixin, MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)


class Caller(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)


async def test_inherited_action_is_discovered(broker, endpoints):
    """Regression test: action/task discovery must walk the full MRO, not
    just the leaf class __dict__, otherwise actions defined on a mixin /
    intermediate base class are silently dropped."""
    sender_endpoint, receiver_endpoint = endpoints

    greeter = GreeterService(sender_endpoint, receiver_endpoint)
    assert 'greet' in greeter.actions

    greeter_task = await run_service(greeter)

    caller = Caller(sender_endpoint, receiver_endpoint)
    caller_task = await run_service(caller)

    result = await asyncio.wait_for(caller.request_action('greet', {}), timeout=2)
    assert result == {'greeting': 'hi'}

    await stop_service(caller_task, caller)
    await stop_service(greeter_task, greeter)
