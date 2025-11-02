VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: venv deps test unit integration lint clean

venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -U pip


deps: venv
	# Install package + dev extras
	$(PIP) install -e .[dev]

# Fast unit tests (only pure-unit tests)
unit: deps
	$(PY) -m pytest -q tests/test_utils.py tests/test_config.py

# Full test suite (integration/emulator tests may be skipped if emulator not present)
integration: deps
	$(PY) -m pytest -q

# Default test target: run unit tests
test: unit

lint: deps
	$(PIP) install ruff black
	ruff check .
	black .

clean:
	rm -rf $(VENV)
	rm -rf build dist *.egg-info
