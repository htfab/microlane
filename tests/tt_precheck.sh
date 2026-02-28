#!/bin/bash
echo '========================'
echo 'running test tt_precheck'
echo '========================'
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/tt_precheck $LOG_DIR/tt_precheck.log
mkdir -p $STEP_DIR/tt_precheck
mkdir -p $LOG_DIR
cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.* $STEP_DIR/tt_precheck/
cp $TEST_ROOT/scripts/info.yaml $STEP_DIR/tt_precheck/
cd $STEP_DIR/tt_precheck
cp tt_um_microlane_demo.pnl.v tt_um_microlane_demo.v
git clone https://github.com/TinyTapeout/tt-support-tools tt
cd tt/precheck
python precheck.py --tech $PDK --gds $STEP_DIR/tt_precheck/tt_um_microlane_demo.gds 2>&1 | tee $LOG_DIR/tt_precheck.log
