SIM = icarus
TOPLEVEL_LANG = verilog
SIM_BUILD = sim_build/gl
COMPILE_ARGS = -DGL_TEST -DFUNCTIONAL -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v
VERILOG_SOURCES += gate_level_netlist.v tb.v
COCOTB_TOPLEVEL = tb
COCOTB_TEST_MODULES = test
include $(shell cocotb-config --makefiles)/Makefile.sim
