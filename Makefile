.PHONY: setup setup-adk test compile demo inspect build docker-build terraform-check clean

setup:
	uv sync --frozen
	uv pip install --python .venv/bin/python -r requirements-dev.txt

setup-adk: setup
	uv pip install --python .venv/bin/python '.[adk]'

test:
	uv run --no-sync python -m pytest

compile:
	uv run --no-sync python -m compileall -q processor examples

demo:
	rm -rf .demo-output
	PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py --output-root .demo-output demo

inspect:
	PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py --output-root .demo-output inspect

build:
	rm -rf build dist ./*.egg-info
	uv run --no-sync python -m build

docker-build:
	docker build -t edge-evidence-processor:local .

terraform-check:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false
	terraform -chdir=terraform validate
	terraform -chdir=terraform test -verbose

clean:
	rm -rf .venv .pytest_cache .ruff_cache .demo-output build dist ./*.egg-info
