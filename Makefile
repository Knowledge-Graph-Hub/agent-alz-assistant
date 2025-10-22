.PHONY: start stop restart install test lint format clean help

# Load environment variables from .env
include .env
export

help:
	@echo "agent-alz-assistant - Makefile commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make start    - Start the application"
	@echo "  make stop     - Stop the application"
	@echo "  make restart  - Restart the application"
	@echo "  make install  - Install dependencies"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Lint code"
	@echo "  make format   - Format code"
	@echo "  make clean    - Clean up temporary files"

install:
	uv sync

start:
	@echo "Clearing port $(PORT)..."
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@echo "Starting agent-alz-assistant on http://localhost:$(PORT)"
	@echo "Login password: see APP_PASSWORD_HASH in .env (default: demo123)"
	uv run python app.py

stop:
	@echo "Stopping application on port $(PORT)..."
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@echo "Application stopped"

restart: stop start

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
