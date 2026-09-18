.DEFAULT_GOAL := help

RTL_DIR := src
TEST_DIR := test

.PHONY: help test unit test-all lint clean

help:
	@echo "Available targets:"
	@echo "  test                 Run top-level cocotb tests"
	@echo "  unit MODULE=<name>   Run unit tests for a module"
	@echo "  test-all             Run all tests"
	@echo "  lint                 Run SystemVerilog linting"
	@echo "  clean                Remove generated test artifacts"

test:
	$(MAKE) -C $(TEST_DIR)

unit:
ifndef MODULE
	$(error MODULE is required. Usage: make unit MODULE=<module>)
endif
	$(MAKE) -C $(TEST_DIR)/unit MODULE=$(MODULE)

test-all:
	$(MAKE) -C $(TEST_DIR)/unit all
	$(MAKE) -C $(TEST_DIR)

lint:
	svlint $(wildcard $(RTL_DIR)/*.sv)

clean:
	$(MAKE) -C $(TEST_DIR) clean
	$(MAKE) -C $(TEST_DIR)/unit clean
