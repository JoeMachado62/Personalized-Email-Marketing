# Makefile for AI Sales Agent MVP

.PHONY: help install dev test build up down clean logs

help: ## Show this help message
	@echo "AI Sales Agent MVP - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	playwright install chromium
	@echo "✅ Dependencies installed"

dev: ## Run development server
	@echo "🚀 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	@echo "🧪 Running tests..."
	pytest tests/ -v
	@echo "✅ Tests completed"

lint: ## Run linting
	@echo "🔍 Running linting..."
	flake8 app/ auto_enrich/ --max-line-length=120
	black app/ auto_enrich/ --check
	@echo "✅ Linting completed"

format: ## Format code
	@echo "📝 Formatting code..."
	black app/ auto_enrich/
	@echo "✅ Code formatted"

build: ## Build Docker images
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Build completed"

up: ## Start Docker containers
	@echo "🚀 Starting containers..."
	docker-compose up -d
	@echo "✅ Containers started"
	@echo "📊 API: http://localhost:8000"
	@echo "🌐 Frontend: http://localhost:3000"

down: ## Stop Docker containers
	@echo "🛑 Stopping containers..."
	docker-compose down
	@echo "✅ Containers stopped"

logs: ## Show container logs
	docker-compose logs -f

clean: ## Clean up generated files and caches
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf *.egg-info
	@echo "✅ Cleanup completed"

db-init: ## Initialize database
	@echo "🗄️ Initializing database..."
	python -c "from app.db.connection import init_db; init_db()"
	@echo "✅ Database initialized"

db-reset: ## Reset database
	@echo "⚠️  Resetting database..."
	rm -f data/app.db
	python -c "from app.db.connection import init_db; init_db()"
	@echo "✅ Database reset"

demo-10: ## Run demo with 10 records
	@echo "🎭 Running 10-record demo..."
	python scripts/demo_10_records.py
	@echo "✅ Demo completed"

demo-100: ## Run demo with 100 records
	@echo "🎭 Running 100-record demo..."
	python scripts/demo_100_records.py
	@echo "✅ Demo completed"

demo-10k: ## Run demo with 10,000 records
	@echo "🎭 Running 10,000-record demo..."
	python scripts/demo_10k_records.py
	@echo "✅ Demo completed"

monitor: ## Monitor system metrics
	@echo "📊 System Monitoring Dashboard"
	watch -n 2 'echo "=== Jobs ===" && sqlite3 data/app.db "SELECT status, COUNT(*) FROM jobs GROUP BY status;" && echo "\n=== Recent Activity ===" && sqlite3 data/app.db "SELECT id, status, total_records, processed_records, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;"'

backup: ## Backup database
	@echo "💾 Backing up database..."
	mkdir -p backups
	cp data/app.db backups/app_$$(date +%Y%m%d_%H%M%S).db
	@echo "✅ Backup completed"

restore: ## Restore latest backup
	@echo "📥 Restoring latest backup..."
	@latest=$$(ls -t backups/*.db | head -1); \
	if [ -n "$$latest" ]; then \
		cp $$latest data/app.db; \
		echo "✅ Restored from $$latest"; \
	else \
		echo "❌ No backup found"; \
	fi