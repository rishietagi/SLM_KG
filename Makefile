# Thin wrappers over `python -m pipeline.cli`; every target also works without make.
PYTHON ?= C:/miniconda/envs/mmsa/python.exe
CLI := $(PYTHON) -m pipeline.cli

.PHONY: gen validate load test report viewer clean all

gen:
	$(CLI) gen

validate:
	$(CLI) validate

load:
	$(CLI) load

test:
	$(PYTHON) -m pytest

report:
	$(CLI) report

viewer:
	$(PYTHON) -m uvicorn viewer.server:app --port 8000

clean:
	$(CLI) clean

all: gen validate load test report
