from aiofase import MicroService

from .conftest import run_service, stop_service, wait_until


class Recorder(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        self.connected = []
        self.new_services = []
        self.broadcasts = []
        self.responses = []
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)

    async def on_connect(self):
        self.connected.append(self.name)

    async def on_new_service(self, service, actions):
        self.new_services.append((service, actions))

    async def on_broadcast(self, service, data):
        self.broadcasts.append((service, data))

    async def on_response(self, service, data):
        self.responses.append((service, data))


class Worker(MicroService):
    def __init__(self, sender_endpoint, receiver_endpoint):
        super().__init__(
            self, sender_endpoint=sender_endpoint, receiver_endpoint=receiver_endpoint, enable_heartbeat=False)

    @MicroService.action
    async def echo(self, service, data):
        return data


async def test_registration_triggers_on_connect_and_on_new_service(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    recorder = Recorder(sender_endpoint, receiver_endpoint)
    recorder_task = await run_service(recorder)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    await wait_until(lambda: 'Recorder' in recorder.connected)
    await wait_until(lambda: any(s == 'Worker' for s, _ in recorder.new_services))

    assert recorder.connected == ['Recorder']
    assert ('Worker', ['echo']) in recorder.new_services

    await stop_service(worker_task, worker)
    await stop_service(recorder_task, recorder)


async def test_broadcast_reaches_other_services_only(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    recorder = Recorder(sender_endpoint, receiver_endpoint)
    recorder_task = await run_service(recorder)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    await worker.send_broadcast({'message': 'hello'})

    await wait_until(lambda: len(recorder.broadcasts) == 1)

    assert recorder.broadcasts == [('Worker', {'message': 'hello'})]

    await stop_service(worker_task, worker)
    await stop_service(recorder_task, recorder)


async def test_direct_response_reaches_on_response(broker, endpoints):
    sender_endpoint, receiver_endpoint = endpoints

    recorder = Recorder(sender_endpoint, receiver_endpoint)
    recorder_task = await run_service(recorder)

    worker = Worker(sender_endpoint, receiver_endpoint)
    worker_task = await run_service(worker)

    await worker.response(recorder.name, {'ack': True})

    await wait_until(lambda: len(recorder.responses) == 1)

    assert recorder.responses == [('Worker', {'ack': True})]

    await stop_service(worker_task, worker)
    await stop_service(recorder_task, recorder)
