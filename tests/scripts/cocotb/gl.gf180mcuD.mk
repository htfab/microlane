SIM = icarus
TOPLEVEL_LANG = verilog
SIM_BUILD = sim_build/gl
COMPILE_ARGS = -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v
VERILOG_SOURCES += gate_level_netlist.v tb.v
COCOTB_TOPLEVEL = tb
COCOTB_TEST_MODULES = test
include $(shell cocotb-config --makefiles)/Makefile.sim
