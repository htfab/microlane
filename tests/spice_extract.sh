#!/bin/bash
echo '=========================='
echo 'running test spice_extract'
echo '=========================='
rm -rf outputs/spice_extract logs/spice_extract.log
mkdir -p outputs/spice_extract
mkdir -p logs
cp outputs/harden_cmdline/tt_um_microlane_demo.gds outputs/spice_extract/
cd outputs/spice_extract
export PDK=sky130A
magic -dnull -noconsole $PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc < ../../scripts/extract.tcl 2>&1 | tee ../../logs/spice_extract.log
