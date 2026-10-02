.DEFAULT_GOAL := help

REPO_ROOT := $(CURDIR)
SRC_DIR := $(REPO_ROOT)/src
TEST_DIR := $(REPO_ROOT)/test
UNIT_TEST_DIR := $(TEST_DIR)/unit
BUILD_DIR := $(REPO_ROOT)/build

export PYTHONPATH := $(TEST_DIR):$(UNIT_TEST_DIR):$(PYTHONPATH)

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

RTL_SOURCES := $(sort \
	$(wildcard $(SRC_DIR)/*.v) \
	$(wildcard $(SRC_DIR)/*.sv) \
)

INTEGRATION_TEST_FILES := $(sort \
	$(wildcard $(TEST_DIR)/test.py) \
	$(wildcard $(TEST_DIR)/test_*.py) \
)

UNIT_TEST_FILES := $(sort $(wildcard $(UNIT_TEST_DIR)/test_*.py))
UNIT_MODULES := $(patsubst test_%,%,$(basename $(notdir $(UNIT_TEST_FILES))))

empty :=
space := $(empty) $(empty)
comma := ,

INTEGRATION_TEST_MODULES := \
	$(subst $(space),$(comma),$(basename $(notdir $(INTEGRATION_TEST_FILES))))

.PHONY: help test tb unit unit-all test-all compile lint check doctor sources tests clean

ifeq ($(COCOTB_RUN),1)

COMPILE_ARGS += -g2012
COMPILE_ARGS += -I$(SRC_DIR)

ifeq ($(MODE),unit)

ifndef MODULE
$(error MODULE is required)
endif

VERILOG_SOURCES := $(RTL_SOURCES)
TOPLEVEL := $(MODULE)
COCOTB_TEST_MODULES := test_$(MODULE)
SIM_BUILD := $(UNIT_TEST_DIR)/sim_build/$(MODULE)

else

ifneq ($(GATES),yes)

VERILOG_SOURCES := $(RTL_SOURCES)
SIM_BUILD := $(TEST_DIR)/sim_build/rtl

else

COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1

VERILOG_SOURCES := \
	$(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v \
	$(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v \
	$(TEST_DIR)/gate_level_netlist.v

SIM_BUILD := $(TEST_DIR)/sim_build/gl

endif

VERILOG_SOURCES += $(TEST_DIR)/tb.sv
TOPLEVEL := tb
COCOTB_TEST_MODULES := $(INTEGRATION_TEST_MODULES)

endif

include $(shell cocotb-config --makefiles)/Makefile.sim

else

help:
	@echo "Available targets:"
	@echo "  make test                  Run all top-level cocotb tests"
	@echo "  make unit MODULE=<name>    Run unit tests for one RTL module"
	@echo "  make unit-all              Run all RTL unit tests"
	@echo "  make test-all              Run all unit and top-level tests"
	@echo "  make compile               Compile all RTL sources"
	@echo "  make lint                  Run svlint"
	@echo "  make check                 Run lint, compile, and all tests"
	@echo "  make doctor                Check required development tools"
	@echo "  make sources               List detected RTL sources"
	@echo "  make tests                 List detected tests"
	@echo "  make clean                 Remove generated files"

test:
	$(MAKE) COCOTB_RUN=1 MODE=integration sim

tb: test

unit:
ifndef MODULE
	$(error MODULE is required. Usage: make unit MODULE=<module_name>)
endif
	$(MAKE) COCOTB_RUN=1 MODE=unit MODULE=$(MODULE) sim

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
	@command -v vvp >/dev/null 2>&1 \
		&& echo "vvp:          OK" \
		|| echo "vvp:          NOT FOUND"
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
	@echo "Top-level tests:"
	@printf '  %s\n' $(basename $(notdir $(INTEGRATION_TEST_FILES)))
	@echo ""
	@echo "Unit tests:"
	@printf '  %s\n' $(UNIT_MODULES)

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(TEST_DIR)/sim_build
	rm -rf $(UNIT_TEST_DIR)/sim_build
	rm -rf results.xml
	rm -rf $(TEST_DIR)/results.xml
	rm -rf $(UNIT_TEST_DIR)/results.xml
	rm -rf __pycache__
	rm -rf $(TEST_DIR)/__pycache__
	rm -rf $(UNIT_TEST_DIR)/__pycache__

endif