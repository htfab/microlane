#!/bin/bash
echo '======================='
echo 'running test cocotb_rtl'
echo '======================='
rm -rf outputs/cocotb_rtl logs/cocotb_rtl.log
mkdir -p outputs/cocotb_rtl
mkdir -p logs
cp src/demo.v outputs/cocotb_rtl/
cp scripts/cocotb/tb.v outputs/cocotb_rtl/
cp scripts/cocotb/test.py outputs/cocotb_rtl/
cp scripts/cocotb/rtl.mk outputs/cocotb_rtl/Makefile
cd outputs/cocotb_rtl
make -B 2>&1 | tee ../../logs/cocotb_rtl.log
