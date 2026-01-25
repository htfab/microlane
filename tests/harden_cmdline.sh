#!/bin/bash
echo '==========================='
echo 'running test harden_cmdline'
echo '==========================='
rm -rf outputs/harden_cmdline logs/harden_cmdline.log
mkdir -p outputs/harden_cmdline
mkdir -p logs
cd outputs/harden_cmdline
microlane ../../src/demo.v 2>&1 | tee ../../logs/harden_cmdline.log
