## 0.5.0 (2026-08-20)

### Feat

- **microservice,server**: support optional ZMQ CURVE encryption
- **security**: add ZMQ CURVE keypair generation/loading helpers
- **microservice**: add heartbeat and on_service_disconnect hook

### Fix

- **microservice,server**: close sockets/context cleanly
- **microservice**: discover actions/tasks across the full class MRO
- **microservice**: route messages by exact prefix, not substring match
- **nodefase**: remove node.js port (moved to its own repository)

## 0.4.1 (2026-05-27)

### Fix

- **microservice**: fix memory leak and race condition in async request tracking

## 0.4.0 (2026-01-22)

### Feat

- **examples/timeout**: creating examples for remote call response, remote execption in execution action and remote timeout execution action
- **microservice**: adding in messages protocol control flow to allow async remote call in actions

### Refactor

- **examples/database**: adding logger with structlog and override print functions

## 0.3.0 (2026-01-21)

### Feat

- **server**: create argument parser to create receiver and sender endpoint

## 0.2.0 (2025-07-04)

### Feat

- first commit
