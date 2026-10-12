# Development Environment (Makefile)

This project uses a `Makefile` to simplify managing the development environment defined in `compose-dev.yaml`.

## Quick Start

To start the entire stack (Portal, API, and Scanner) in the background:

```bash
make up
```

## Available Commands

| Command | Description | Docker Equivalent |
| :--- | :--- | :--- |
| `make up` | Starts services in detached mode | `docker compose -f compose-dev.yaml up -d` |
| `make down` | Stops and removes containers | `docker compose -f compose-dev.yaml down` |
| `make restart` | Restarts all services | `docker compose -f compose-dev.yaml restart` |
| `make build` | Builds images for services | `docker compose -f compose-dev.yaml build` |
| `make build-no-cache` | Builds images from scratch | `docker compose -f compose-dev.yaml build --no-cache` |
| `make logs` | Tail logs for all services | `docker compose -f compose-dev.yaml logs -f` |
| `make clean` | Stops services and deletes volumes | `docker compose -f compose-dev.yaml down -v` |
| `make shell-api` | Enters shell of the API container | `docker compose -f compose-dev.yaml exec api sh` |
| `make shell-portal` | Enters shell of the Portal container | `docker compose -f compose-dev.yaml exec portal sh` |

## Common Workflows

### Updating Code
If you've made changes to the API or Portal and need to rebuild:
```bash
make down
make build
make up
```

### Debugging
To view real-time logs while the app is running:
```bash
make logs
```

To run a command inside the API container (e.g., checking database state):
```bash
make shell-api
```

### Resetting the Environment
To wipe all data (including the SQLite database volume) and start fresh:
```bash
make clean
make up
```
