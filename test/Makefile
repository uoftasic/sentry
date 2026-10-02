# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR := $(abspath $(CURDIR)/../src)

# Automatically include all Verilog/SystemVerilog RTL sources.
PROJECT_SOURCES := $(sort \
	$(wildcard $(SRC_DIR)/*.v) \
	$(wildcard $(SRC_DIR)/*.sv) \
)

ifneq ($(GATES),yes)

# RTL simulation
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(PROJECT_SOURCES)

else

# Gate-level simulation
SIM_BUILD = sim_build/gl

COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1

VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

# Copied in by the TinyTapeout GDS workflow.
VERILOG_SOURCES += $(CURDIR)/gate_level_netlist.v

endif

COMPILE_ARGS += -g2012
COMPILE_ARGS += -I$(SRC_DIR)

VERILOG_SOURCES += $(CURDIR)/tb.sv

TOPLEVEL = tb
COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim