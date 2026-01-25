#!/bin/bash
echo '======================'
echo 'running test cocotb_gl'
echo '======================'
rm -rf outputs/cocotb_gl logs/cocotb_gl.log
mkdir -p outputs/cocotb_gl
mkdir -p logs
cp outputs/harden_cmdline/tt_um_microlane_demo.pnl.v outputs/cocotb_gl/gate_level_netlist.v
cp scripts/cocotb/tb.v outputs/cocotb_gl/
cp scripts/cocotb/test.py outputs/cocotb_gl/
cp scripts/cocotb/gl.mk outputs/cocotb_gl/Makefile
cd outputs/cocotb_gl
GATES=yes make -B 2>&1 | tee ../../logs/cocotb_gl.log
