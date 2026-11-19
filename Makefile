# Evidence Integrity Platform (EIP) - Developer Automation

.PHONY: help install backend frontend test seed docker docker-down clean

help:
	@echo "Evidence Integrity Platform - Developer Commands"
	@echo "------------------------------------------------"
	@echo "  make install      Install backend and frontend dependencies"
	@echo "  make backend      Run FastAPI backend dev server"
	@echo "  make frontend     Run React/Vite frontend dev server"
	@echo "  make test         Execute automated test suite (pytest)"
	@echo "  make seed         Seed realistic demo cases & evidence"
	@echo "  make docker       Build and start full-stack in Docker"
	@echo "  make docker-down  Stop and tear down Docker containers"
	@echo "  make clean        Remove cache, build artifacts, and temp files"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd frontend && npm run dev

test:
	pytest tests/ -v

seed:
	cd backend && python scripts/seed_demo.py

docker:
	docker compose up --build

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
