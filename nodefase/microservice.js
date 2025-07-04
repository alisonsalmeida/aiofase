// const sender = zmq.socket('push')
// sender.connect('ipc:///tmp/receiver')
// sender.send('ola mundo')
//
// const receiver = zmq.socket('sub')
// receiver.connect('ipc:///tmp/sender')
// receiver.subscribe('')
//
// receiver.on('message', function(msg){
//   console.log('work: %s', msg.toString());
// });

const zmq = require('zeromq')

module.exports = class Microservice {
  constructor(sender_endpoint, receiver_endpoint, name) {
    this._actions = {}
    this._tasks = {}
    this._events = {}
    this._names_event = ['on_connect', 'on_new_service', 'on_response', 'on_broadcast']
    this.name = name

    this.sender_endpoint = sender_endpoint
    this.receiver_endpoint = receiver_endpoint

    this.sender = zmq.socket('push')
    this.sender.connect(this.receiver_endpoint)

    this.receiver = zmq.socket('sub')
    this.receiver.connect(this.sender_endpoint)
    this.receiver.subscribe('')

    this.receiver.on('message', (msg) => this.execute(msg))
  }

  start() {
    const actions = []

    Object.keys(this._actions).forEach((key, index) => {
      actions.push(key);

      if (index + 1 === Object.keys(this._actions).length) {
        const json_data = {'s': this.name, 'a': actions}
        const data_to_register = '<r>:' + JSON.stringify(json_data)
        this.sender.send(data_to_register)
      }
    })
    console.log('starting')
  }

  on(eventType, fn) {
    if (this._names_event.includes(eventType)) {
      this._events[eventType] = fn
    }

    else {
      this._actions[eventType] = fn;
    }
  }

  send_broadcast(data) {
    const data_to_send = '<b>:' + JSON.stringify({'s': this.name, 'd': data})
    this.sender.send(data_to_send)
  }

  request_action(action, data) {
    const data_to_send = action + ':' + JSON.stringify({'s': this.name, 'd': data})
  }

  response(service, data) {
    const data_to_send = {'s': this.name, 'd': data}
    const content = service + ':' + JSON.stringify(data_to_send)
    this.sender.send(content)
  }

  execute(msg) {
    try {
      const message = msg.toString()

      if (message.indexOf('<r>:') === 0) {
        const payload = JSON.parse(message.slice(4))
        const service = payload['s']
        const actions = payload['a']

        if (this.name === service && 'on_connect' in this._events) {
          this._events['on_connect']()
        }
        else if ('on_new_service' in this._events) {
          this._events['on_new_service'](service, actions)
        }
      }

      else if (message.indexOf('<b>:') === 0) {
        const payload = JSON.parse(message.slice(4))
        const service = payload['s']
        const data = payload['d']

        if (this.name !== service && 'on_broadcast' in this._events) {
          this._events['on_broadcast'](service. data)
        }
      }

      else if (message.indexOf(this.name + ':') > 0) {
        const index = message.indexOf(this.name + ':')
        const action = message.slice(0, index)
        let content = message.slice(index + 1)
        content = JSON.parse(content)
        const service = content['s']
        const data = content['d']

        if ('on_response' in this._events) {
          this._events['on_response'](service, data)
        }
      }

      else {
        const content = message.indexOf(':')
        const action = message.slice(0, content)
        let data = message.slice(content + 1)

        if (action in this._actions) {
          data = JSON.parse(data)
          this._actions[action](data['s'], data['d'])
        }
      }
    }
    catch (e) {
      console.error('fail to decode message: ', e)
    }
  }
}
