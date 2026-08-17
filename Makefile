.PHONY: setup setup-contributor test clean

setup:
	uv venv
	uv pip install -e .

setup-contributor:
	uv venv
	uv pip install -e '.[contributor]'

test:
	uv run pytest

clean:
	rm -rf .venv
