# Makefile for crossplane-mcp-server

.PHONY: run-server run-client test test-server test-client lint format help

run-server:
	uv run src/server/server.py

run-client:
	uv run src/client/client.py

test:  ## Run all tests
	uv run -m unittest discover -s src

test-server:
	uv run -m unittest src/server/test_server.py

test-client:
	uv run -m unittest src/client/test_client.py

lint: ## Lint the codebase
	uv run ruff check .

format: ## Format the codebase
	uv run ruff format .

help: ## Display this help screen
	@grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'