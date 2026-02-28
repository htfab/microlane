#!/bin/bash
echo '================'
echo 'running test drc'
echo '================'
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/drc $LOG_DIR/drc.log
mkdir -p $STEP_DIR/drc
mkdir -p $LOG_DIR
cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.gds $STEP_DIR/drc/
cd $STEP_DIR/drc
magic -dnull -noconsole $PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc < $TEST_ROOT/scripts/drc.tcl 2>&1 | tee $LOG_DIR/drc.log
