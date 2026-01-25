#!/bin/bash
echo '========================'
echo 'running test tt_precheck'
echo '========================'
rm -rf outputs/tt_precheck logs/tt_precheck.log
mkdir -p outputs/tt_precheck
mkdir -p logs
cp outputs/harden_cmdline/tt_um_microlane_demo.* outputs/tt_precheck/
cp scripts/info.yaml outputs/tt_precheck/
cd outputs/tt_precheck
cp tt_um_microlane_demo.pnl.v tt_um_microlane_demo.v
git clone https://github.com/TinyTapeout/tt-support-tools tt
cd tt/precheck
python precheck.py --tech sky130A --gds ../../tt_um_microlane_demo.gds 2>&1 | tee ../../../../logs/tt_precheck.log
