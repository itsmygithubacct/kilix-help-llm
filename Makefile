PYTHON ?= python3

.PHONY: check
check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v
