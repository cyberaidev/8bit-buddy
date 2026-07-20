.PHONY: test check install

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

check:
	python3 -m compileall -q src
	PYTHONPATH=src python3 -m unittest discover -s tests -v

install:
	python3 -m pip install -e .
