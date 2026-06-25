.PHONY: up down build logs shell test lint migrate

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Rebuild images
build:
	docker-compose build

# Tail logs
logs:
	docker-compose logs -f backend

# Open a shell inside the backend container
shell:
	docker-compose exec backend bash

# Run database migrations
migrate:
	docker-compose exec backend alembic upgrade head

# Run tests inside container
test:
	docker-compose exec backend pytest tests/ -v

# Run linting
lint:
	docker-compose exec backend ruff check app/

# Stop and remove volumes (clean slate)
clean:
	docker-compose down -v