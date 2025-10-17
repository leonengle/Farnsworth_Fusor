# Makefile for Farnsworth Fusor Project

.PHONY: help install test clean

help:
	@echo "Available targets:"
	@echo "  install  - Install dependencies"
	@echo "  test     - Run tests"
	@echo "  clean    - Clean up generated files"

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
