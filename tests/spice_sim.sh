#!/bin/bash
echo '======================'
echo 'running test spice_sim'
echo '======================'
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/spice_sim $LOG_DIR/spice_sim.log
mkdir -p $STEP_DIR/spice_sim
mkdir -p $LOG_DIR
cp $TEST_ROOT/scripts/sim.$PDK.spice $STEP_DIR/spice_sim/sim.spice
cp $TEST_ROOT/scripts/viewer.sch $STEP_DIR/spice_sim/
cp $STEP_DIR/spice_extract/tt_um_microlane_demo.spice $STEP_DIR/spice_sim/
cd $STEP_DIR/spice_sim
stdbuf -oL ngspice -batch sim.spice 2>&1 | tee $LOG_DIR/spice_sim.log
