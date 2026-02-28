#!/bin/bash
echo '=========================='
echo 'running test harden_script'
echo '=========================='
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/harden_script $LOG_DIR/harden-script.log
mkdir -p $STEP_DIR/harden_script
mkdir -p $LOG_DIR
cd $STEP_DIR/harden_script
$TEST_ROOT/scripts/harden.py 2>&1 | tee $LOG_DIR/harden_script.log
