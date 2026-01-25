#!/bin/bash
echo '=========================='
echo 'running test harden_script'
echo '=========================='
rm -rf outputs/harden_script logs/harden-script.log
mkdir -p outputs/harden_script
mkdir -p logs
cd outputs/harden_script
../../scripts/harden.py 2>&1 | tee ../../logs/harden_script.log
