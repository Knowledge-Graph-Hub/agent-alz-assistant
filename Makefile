.PHONY: start stop restart install test lint format clean deploy logs help

# Load environment variables from .env
include .env
export

# Deployment configuration
DEPLOY_HOST ?= gassh
DEPLOY_DIR ?= ~/agent-alz-assistant
LOCAL_DATA_DIR ?= data

help:
	@echo "agent-alz-assistant - Makefile commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make start    - Start the application"
	@echo "  make stop     - Stop the application"
	@echo "  make restart  - Restart the application"
	@echo "  make logs     - Tail the most recent log file"
	@echo "  make install  - Install dependencies"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Lint code"
	@echo "  make format   - Format code"
	@echo "  make clean    - Clean up temporary files"
	@echo "  make deploy   - Deploy to production server (gassh)"

install:
	uv sync

start:
	@echo "Clearing port $(PORT)..."
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@mkdir -p logs
	@echo "Starting agent-alz-assistant on http://localhost:$(PORT)"
	@echo "Login password: see APP_PASSWORD_HASH in .env"
	@LOGFILE="logs/app_$$(date +%Y%m%d_%H%M%S).log"; \
	echo "Logs: tail -f $$LOGFILE"; \
	nohup uv run python app.py > $$LOGFILE 2>&1 &
	@echo "Application started in background"

stop:
	@echo "Stopping application on port $(PORT)..."
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	@echo "Application stopped"

restart: stop start

logs:
	@if [ -d logs ] && [ -n "$$(ls -t logs/app_*.log 2>/dev/null | head -1)" ]; then \
		LATEST_LOG=$$(ls -t logs/app_*.log | head -1); \
		echo "Tailing $$LATEST_LOG"; \
		tail -f $$LATEST_LOG; \
	else \
		echo "No log files found in logs/"; \
		exit 1; \
	fi

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

deploy:
	@echo "========================================="
	@echo "Deploying agent-alz-assistant to $(DEPLOY_HOST)"
	@echo "========================================="
	@echo ""
	@echo "Step 1: Ensuring repository exists on $(DEPLOY_HOST)..."
	@ssh $(DEPLOY_HOST) "if [ ! -d $(DEPLOY_DIR)/.git ]; then \
		echo 'Repository not found, cloning...'; \
		git clone https://github.com/Knowledge-Graph-Hub/agent-alz-assistant.git $(DEPLOY_DIR); \
	else \
		echo 'Repository exists, pulling latest changes...'; \
		cd $(DEPLOY_DIR) && git pull; \
	fi"
	@echo ""
	@echo "Step 2: Creating data directory on $(DEPLOY_HOST)..."
	@ssh $(DEPLOY_HOST) "mkdir -p $(DEPLOY_DIR)/data"
	@echo ""
	@echo "Step 3: Uploading paper corpus..."
	@rsync -avz --progress $(LOCAL_DATA_DIR)/alz_papers_1k_text/ $(DEPLOY_HOST):$(DEPLOY_DIR)/data/alz_papers_1k_text/
	@echo ""
	@echo "Step 4: Uploading PaperQA index..."
	@rsync -avz --progress $(LOCAL_DATA_DIR)/pqa_index_*/ $(DEPLOY_HOST):$(DEPLOY_DIR)/data/pqa_index_*/
	@echo ""
	@echo "Step 5: Checking .env configuration on $(DEPLOY_HOST)..."
	@ssh $(DEPLOY_HOST) "if [ ! -f $(DEPLOY_DIR)/.env ]; then \
		echo 'WARNING: .env does not exist on server!'; \
		echo 'You need to create it manually:'; \
		echo '  1. ssh $(DEPLOY_HOST)'; \
		echo '  2. cd $(DEPLOY_DIR) && cp .env.example .env'; \
		echo '  3. Edit .env with production values (STORAGE_SECRET, APP_PASSWORD_HASH, etc.)'; \
		echo 'Deployment will continue, but app will not start without .env'; \
	else \
		echo '.env already exists - preserving existing configuration'; \
	fi"
	@echo ""
	@echo "Step 6: Installing dependencies on $(DEPLOY_HOST)..."
	@ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && ~/.local/bin/uv sync"
	@echo ""
	@echo "Step 7: Starting application on $(DEPLOY_HOST)..."
	@ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && PATH=\$$HOME/.local/bin:\$$PATH make start"
	@echo ""
	@echo "========================================="
	@echo "Deployment complete!"
	@echo "Application should be running at http://agent.alzassistant.org"
	@echo "========================================="
