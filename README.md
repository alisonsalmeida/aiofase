# 🛰️ Async MicroService Framework com ZeroMQ

Este projeto é um framework leve e assíncrono para criar microsserviços em Python, utilizando `zmq.asyncio` como mecanismo de comunicação entre processos ou entre máquinas.

## 🚀 Recursos

- 📡 Comunicação assíncrona entre microsserviços com ZeroMQ (PUSH/PULL + PUB/SUB)
- 🧠 Suporte a ações (`@action`) e tarefas (`@task`) com execução assíncrona
- 📢 Suporte a mensagens broadcast, requisições diretas e respostas
- 🔌 Sistema de descoberta de serviços simples e leve
- ⚙️ Customização com hooks para eventos (`on_connect`, `on_new_service`, etc.)

## 📦 Requisitos

- Python 3.8+
- `pyzmq`
- `asyncio`

```bash
poetry install
```

## Exemplo de Uso

```python
class MyService:
    @MicroService.action
    async def hello(self, origin, data):
        print(f"Recebido de {origin}: {data}")

    @MicroService.task
    async def heartbeat(self):
        while True:
            await asyncio.sleep(5)
            print("Estou vivo")

if __name__ == '__main__':
    service = MicroService(
        service=MyService(),
        sender_endpoint='ipc:///tmp/sender', # tcp://0.0.0.0:3000
        receiver_endpoint='ipc:///tmp/receiver' # tcp://0.0.0.0:4000
    )
    asyncio.run(service.run())
```

## 📡 Fluxo de Mensagens

- Registro: ao iniciar, um serviço envia uma mensagem <r> com suas ações disponíveis.

- Broadcast: mensagens <b> são enviadas para todos os serviços.

- Ação direta: mensagens com prefixo action: disparam métodos marcados como @action.

- Resposta direta: mensagens com prefixo service_name: retornam dados diretamente ao solicitante.

## 🧩 Arquitetura

```markdown
┌──────────────┐        PUSH        ┌──────────────┐
│ MicroService │ ─────────────────▶ │   Receiver   │
└──────────────┘                    └──────────────┘
     ▲
     │
 SUB │
     ▼
┌──────────────┐
│   Sender     │
└──────────────┘
```

## 🔄 Integração com outros sistemas

- Pode ser facilmente integrado com sensores IoT, bancos de dados, interfaces HTTP ou MQTT.

- Ideal para arquiteturas orientadas a eventos com múltiplos serviços independentes.