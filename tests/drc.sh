#!/bin/bash
echo '================'
echo 'running test drc'
echo '================'
rm -rf outputs/drc logs/drc.log
mkdir -p outputs/drc
mkdir -p logs
cp outputs/harden_cmdline/tt_um_microlane_demo.gds outputs/drc/
cd outputs/drc
export PDK=sky130A
magic -dnull -noconsole $PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc < ../../scripts/drc.tcl 2>&1 | tee ../../logs/drc.log
