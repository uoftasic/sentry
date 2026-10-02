SIM ?= icarus
TOPLEVEL_LANG ?= verilog

ifndef MODULE
$(error MODULE is required. Usage: make MODULE=<module_name>)
endif

REPO_ROOT := $(abspath $(CURDIR)/../..)
SRC_DIR := $(REPO_ROOT)/src

RTL_SOURCES := $(sort \
	$(wildcard $(SRC_DIR)/*.v) \
	$(wildcard $(SRC_DIR)/*.sv) \
)

VERILOG_SOURCES := $(RTL_SOURCES)

COMPILE_ARGS += -g2012
COMPILE_ARGS += -I$(SRC_DIR)

TOPLEVEL := $(MODULE)
COCOTB_TEST_MODULES := test_$(MODULE)

SIM_BUILD := $(CURDIR)/sim_build/$(MODULE)

export PYTHONPATH := $(CURDIR):$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim