COMPOSE_FILE=compose-dev.yaml

.PHONY: up down restart build build-no-cache logs clean shell-api shell-portal

# Start the services in detached mode
up:
	docker compose -f $(COMPOSE_FILE) up -d

# Stop and remove containers
down:
	docker compose -f $(COMPOSE_FILE) down

# Restart the services
restart:
	docker compose -f $(COMPOSE_FILE) restart

# Build the images
build:
	docker compose -f $(COMPOSE_FILE) build

# Build from scratch (no cache)
build-no-cache:
	docker compose -f $(COMPOSE_FILE) build --no-cache

# Follow logs for all services
logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# Stop services and remove volumes
clean:
	docker compose -f $(COMPOSE_FILE) down -v

# Open a shell in the api container
shell-api:
	docker compose -f $(COMPOSE_FILE) exec api sh

# Open a shell in the portal container
shell-portal:
	docker compose -f $(COMPOSE_FILE) exec portal sh
