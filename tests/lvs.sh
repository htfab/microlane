#!/bin/bash
echo '================'
echo 'running test lvs'
echo '================'
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/lvs $LOG_DIR/lvs.log
mkdir -p $STEP_DIR/lvs
mkdir -p $LOG_DIR
cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.pnl.v $STEP_DIR/lvs/gate_level_netlist.v
cp $STEP_DIR/spice_extract/tt_um_microlane_demo.spice $STEP_DIR/lvs/
cd $STEP_DIR/lvs
$TEST_ROOT/scripts/lvs.py 2>&1 | tee $LOG_DIR/lvs.log
