#!/bin/bash
echo '======================'
echo 'running test spice_sim'
echo '======================'
rm -rf outputs/spice_sim logs/spice_sim.log
mkdir -p outputs/spice_sim
mkdir -p logs
cp scripts/sim.spice outputs/spice_sim/
cp scripts/viewer.sch outputs/spice_sim/
cp outputs/spice_extract/tt_um_microlane_demo.spice outputs/spice_sim/
cd outputs/spice_sim
export PDK=sky130A
stdbuf -oL ngspice -batch sim.spice 2>&1 | tee ../../logs/spice_sim.log
