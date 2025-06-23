# Makefile for crossplane-mcp-server

.PHONY: run-server run-client test test-server test-client

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
