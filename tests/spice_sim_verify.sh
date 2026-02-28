#!/bin/bash
echo '============================='
echo 'running test spice_sim_verify'
echo '============================='
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/spice_sim_verify $LOG_DIR/spice_sim_verify.log
mkdir -p $STEP_DIR/spice_sim_verify
mkdir -p $LOG_DIR
cp $STEP_DIR/spice_sim/sim.raw $STEP_DIR/spice_sim_verify/
cd $STEP_DIR/spice_sim_verify
$TEST_ROOT/scripts/verify_sim.py 2>&1 | tee $LOG_DIR/spice_sim_verify.log
