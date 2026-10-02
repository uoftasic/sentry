.DEFAULT_GOAL := help

SRC_DIR := src
TEST_DIR := test
UNIT_TEST_DIR := $(TEST_DIR)/unit
BUILD_DIR := build

RTL_SOURCES := $(sort \
	$(wildcard $(SRC_DIR)/*.v) \
	$(wildcard $(SRC_DIR)/*.sv) \
)

UNIT_TEST_FILES := $(sort $(wildcard $(UNIT_TEST_DIR)/test_*.py))
UNIT_MODULES := $(patsubst test_%,%,$(basename $(notdir $(UNIT_TEST_FILES))))

.PHONY: help test unit unit-all test-all gate-test compile lint check doctor sources tests clean

help:
	@echo "Available targets:"
	@echo "  make test                  Run integration tests"
	@echo "  make unit MODULE=<name>    Run unit test for one RTL module"
	@echo "  make unit-all              Run all detected unit tests"
	@echo "  make test-all              Run unit and integration tests"
	@echo "  make gate-test             Run gate-level integration tests"
	@echo "  make compile               Compile all RTL sources"
	@echo "  make lint                  Run svlint"
	@echo "  make check                 Run lint, compile, and all tests"
	@echo "  make doctor                Check required tools"
	@echo "  make sources               List detected RTL sources"
	@echo "  make tests                 List detected unit tests"
	@echo "  make clean                 Remove generated files"

test:
	$(MAKE) -C $(TEST_DIR)

unit:
ifndef MODULE
	$(error MODULE is required. Usage: make unit MODULE=<module_name>)
endif
	$(MAKE) -C $(UNIT_TEST_DIR) MODULE=$(MODULE)

unit-all:
	@if [ -z "$(strip $(UNIT_MODULES))" ]; then \
		echo "No unit tests found."; \
	else \
		set -e; \
		for module in $(UNIT_MODULES); do \
			echo "==> Running unit test: $$module"; \
			$(MAKE) unit MODULE=$$module; \
		done; \
	fi

test-all: unit-all test

gate-test:
	$(MAKE) -C $(TEST_DIR) GATES=yes

compile:
	@mkdir -p $(BUILD_DIR)
	iverilog \
		-g2012 \
		-Wall \
		-I$(SRC_DIR) \
		-o $(BUILD_DIR)/sentry.vvp \
		$(RTL_SOURCES)

lint:
	svlint $(RTL_SOURCES)

check: lint compile test-all

doctor:
	@command -v git >/dev/null 2>&1 \
		&& echo "git:          OK" \
		|| echo "git:          NOT FOUND"
	@command -v make >/dev/null 2>&1 \
		&& echo "make:         OK" \
		|| echo "make:         NOT FOUND"
	@command -v iverilog >/dev/null 2>&1 \
		&& echo "iverilog:     OK" \
		|| echo "iverilog:     NOT FOUND"
	@command -v svlint >/dev/null 2>&1 \
		&& echo "svlint:       OK" \
		|| echo "svlint:       NOT FOUND"
	@command -v python3 >/dev/null 2>&1 \
		&& echo "python3:      OK" \
		|| echo "python3:      NOT FOUND"
	@command -v cocotb-config >/dev/null 2>&1 \
		&& echo "cocotb:       OK" \
		|| echo "cocotb:       NOT FOUND"

sources:
	@printf '%s\n' $(RTL_SOURCES)

tests:
	@if [ -z "$(strip $(UNIT_MODULES))" ]; then \
		echo "No unit tests found."; \
	else \
		printf '%s\n' $(UNIT_MODULES); \
	fi

clean:
	$(MAKE) -C $(TEST_DIR) clean
	$(MAKE) -C $(UNIT_TEST_DIR) clean
	rm -rf $(BUILD_DIR)