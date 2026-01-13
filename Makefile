.PHONY: run check

run:
	python -m lathe.main

check:
	pytest -q