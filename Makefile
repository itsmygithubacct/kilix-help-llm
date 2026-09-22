PYTHON ?= python3

.PHONY: check check-runtime
check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check-runtime:
	PYTHONDONTWRITEBYTECODE=1 "$${GPU_TERMINAL_HOME:-$$HOME/.local/gpu_terminal}/kilix-help-llm/runtimes/cpu/bin/python" -m unittest discover -s tests -v
