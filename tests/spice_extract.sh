#!/bin/bash
echo '=========================='
echo 'running test spice_extract'
echo '=========================='
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/spice_extract $LOG_DIR/spice_extract.log
mkdir -p $STEP_DIR/spice_extract
mkdir -p $LOG_DIR
cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.gds $STEP_DIR/spice_extract/
cd $STEP_DIR/spice_extract
magic -dnull -noconsole $PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc < $TEST_ROOT/scripts/extract.tcl 2>&1 | tee $LOG_DIR/spice_extract.log
