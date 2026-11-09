SIM ?= icarus
TOPLEVEL_LANG ?= verilog

ifneq ($(MAKECMDGOALS),clean)
ifndef DUT_MODULE
$(error DUT_MODULE is required. Usage: make DUT_MODULE=<module_name>)
endif
endif

# The outer Makefile uses MODULE as its public selector. Clear the legacy
# cocotb variables before including cocotb's simulator Makefile.
override MODULE :=
override TOPLEVEL :=

REPO_ROOT := $(abspath $(CURDIR)/../..)
SRC_DIR := $(REPO_ROOT)/src

RTL_SOURCES := $(sort \
	$(wildcard $(SRC_DIR)/*.v) \
	$(wildcard $(SRC_DIR)/*.sv) \
)

VERILOG_SOURCES := $(RTL_SOURCES)

COMPILE_ARGS += -g2012
COMPILE_ARGS += -I$(SRC_DIR)

COCOTB_TOPLEVEL := $(DUT_MODULE)
COCOTB_TEST_MODULES := test_$(DUT_MODULE)

SIM_BUILD := $(CURDIR)/sim_build/$(DUT_MODULE)

export PYTHONPATH := $(CURDIR):$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim

WAVES ?= 1