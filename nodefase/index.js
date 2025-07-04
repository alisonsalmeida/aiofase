const MS = require('./microservice')
ms = new MS('ipc:///tmp/sender', 'ipc:///tmp/receiver', 'ListenerJS')
ms.on('save_data', (service, data) => {
    console.log('salvando dados de ', service, ' ', data)
    ms.response(service, data)
})

ms.on('on_connect', () => {
    console.log('connect to server');
})

ms.start()