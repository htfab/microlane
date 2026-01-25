#!/bin/bash
echo '=========================='
echo 'running test harden_module'
echo '=========================='
rm -rf outputs/harden_module
mkdir -p outputs/harden_module
mkdir -p logs
cd outputs/harden_module
python -m microlane ../../src/demo.v 2>&1 | tee ../../logs/harden_module.log
