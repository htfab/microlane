#!/bin/bash
echo '============================='
echo 'running test spice_sim_verify'
echo '============================='
rm -rf outputs/spice_sim_verify logs/spice_sim_verify.log
mkdir -p outputs/spice_sim_verify
mkdir -p logs
cp outputs/spice_sim/sim.raw outputs/spice_sim_verify/
cd outputs/spice_sim_verify
../../scripts/verify_sim.py 2>&1 | tee ../../logs/spice_sim_verify.log
