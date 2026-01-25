SIM = icarus
TOPLEVEL_LANG = verilog
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES = demo.v tb.v
COCOTB_TOPLEVEL = tb
COCOTB_TEST_MODULES = test
include $(shell cocotb-config --makefiles)/Makefile.sim
