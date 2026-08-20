# 🛰️ Async MicroService Framework com ZeroMQ

Este projeto é um framework leve e assíncrono para criar microsserviços em Python, utilizando `zmq.asyncio` como mecanismo de comunicação entre processos ou entre máquinas.

## 🚀 Recursos

- 📡 Comunicação assíncrona entre microsserviços com ZeroMQ (PUSH/PULL + PUB/SUB)
- 🧠 Suporte a ações (`@action`) e tarefas (`@task`) com execução assíncrona
- 📢 Suporte a mensagens broadcast, requisições diretas e respostas
- 🔌 Sistema de descoberta de serviços, incluindo detecção de desconexão via heartbeat
- ⚙️ Customização com hooks para eventos (`on_connect`, `on_new_service`, `on_service_disconnect`, etc.)
- 🔐 Criptografia e autenticação opcionais via ZMQ CURVE (Curve25519/libsodium)

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

- Heartbeat: mensagens <hb> são enviadas periodicamente por cada serviço; se um serviço para de
  enviar sinais por `heartbeat_timeout` segundos, o hook `on_service_disconnect(service)` é
  disparado nos demais serviços que o conheciam.

## 💓 Heartbeat e detecção de desconexão

Por padrão, todo `MicroService` envia um heartbeat periódico e monitora os heartbeats dos demais
serviços conhecidos. Isso permite detectar quando um serviço cai sem avisar (crash, queda de
rede, etc.), não só quando ele se conecta.

```python
service = MicroService(
    service=MyService(),
    sender_endpoint='tcp://0.0.0.0:3000',
    receiver_endpoint='tcp://0.0.0.0:4000',
    enable_heartbeat=True,       # padrão: True
    heartbeat_interval=5,        # segundos entre heartbeats (padrão: 5)
    heartbeat_timeout=15,        # segundos sem sinal até considerar desconectado (padrão: 3x o intervalo)
)
```

```python
class MyService:
    async def on_service_disconnect(self, service: str):
        print(f'{service} parou de responder')
```

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

## 🔐 Criptografia

O `aiofase` suporta criptografia e autenticação de ponta a ponta via **ZMQ CURVE**
(Curve25519/libsodium, nativo do `pyzmq`). É opcional e desligada por padrão.

### 1. Gerar as chaves

Cada serviço (e o broker) precisa de um par de chaves CURVE. Gere com o CLI do módulo
`aiofase.security`:

```bash
python -m aiofase.security --name broker --out ./keys
python -m aiofase.security --name meu_servico --out ./keys
```

Isso cria `broker.key` (pública, pode compartilhar) e `broker.key_secret`.

### 2. Habilitar no broker

```python
server = Server(
    sender_endpoint='tcp://0.0.0.0:3000',
    receiver_endpoint='tcp://0.0.0.0:4000',
    curve_secretkey_file='./keys/broker.key_secret',
    authorized_clients_dir='./keys/authorized_clients',  # opcional, veja abaixo
)
```

Ou via CLI: `python -m aiofase.server --curve-secretkey-file ./keys/broker.key_secret`.

- Com `authorized_clients_dir`: só clientes cuja chave pública (`.key`) esteja nesse diretório
  conseguem conectar — criptografia **e** autenticação.
- Sem `authorized_clients_dir`: qualquer par de chaves CURVE válido é aceito — só
  criptografia, sem controle de quem conecta (`CURVE_ALLOW_ANY`).

### 3. Habilitar no MicroService

```python
service = MicroService(
    service=MyService(),
    sender_endpoint='tcp://0.0.0.0:3000',
    receiver_endpoint='tcp://0.0.0.0:4000',
    curve_secretkey_file='./keys/meu_servico.key_secret',
    server_publickey_file='./keys/broker.key',
)
```

Os dois parâmetros (`curve_secretkey_file` e `server_publickey_file`) são obrigatórios em conjunto.

## 🧪 Testes

A suíte usa `pytest` + `pytest-asyncio`, com testes de integração reais (sobem `Server` e `MicroService` de verdade sobre sockets `ipc://` temporários.

```bash
poetry install
pytest tests/ --cov=aiofase --cov-report=term-missing
```

O `--cov-report=term-missing` mostra, por arquivo, quais linhas ainda não têm teste. Para um
relatório HTML navegável:

```bash
pytest tests/ --cov=aiofase --cov-report=html
# abre htmlcov/index.html
```

## 🔄 Integração com outros sistemas

- Pode ser facilmente integrado com sensores IoT, bancos de dados, interfaces HTTP ou MQTT.

- Ideal para arquiteturas orientadas a eventos com múltiplos serviços independentes.