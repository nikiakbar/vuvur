COMPOSE_FILE=compose-dev.yaml

.PHONY: up up-f down restart build build-no-cache logs clean shell-api shell-portal

# Start the services in detached mode
up:
	docker compose -f $(COMPOSE_FILE) up -d

# Start the services in the foreground
up-f:
	docker compose -f $(COMPOSE_FILE) up

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
	docker compose -f $(COMPOSE_FILE) stop
	@echo "Services stopped. Pausing for 5 seconds before removing volumes and networks..."
	sleep 5
	docker compose -f $(COMPOSE_FILE) down -v
	rm -rf logs
	@echo "Local logs removed."

# Open a shell in the api container
shell-api:
	docker compose -f $(COMPOSE_FILE) exec api sh

# Open a shell in the portal container
shell-portal:
	docker compose -f $(COMPOSE_FILE) exec portal sh
