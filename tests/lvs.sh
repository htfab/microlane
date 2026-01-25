#!/bin/bash
echo '================'
echo 'running test lvs'
echo '================'
rm -rf outputs/lvs logs/lvs.log
mkdir -p outputs/lvs
mkdir -p logs
cp outputs/harden_cmdline/tt_um_microlane_demo.pnl.v outputs/lvs/gate_level_netlist.v
cp outputs/spice_extract/tt_um_microlane_demo.spice outputs/lvs/
cd outputs/lvs
../../scripts/lvs.py 2>&1 | tee ../../logs/lvs.log
