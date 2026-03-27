#!/bin/bash
echo '======================='
echo 'running test cocotb_rtl'
echo '======================='
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/cocotb_rtl $LOG_DIR/cocotb_rtl.log
mkdir -p $STEP_DIR/cocotb_rtl
mkdir -p $LOG_DIR
cp $TEST_ROOT/src/demo.v $STEP_DIR/cocotb_rtl/
cp $TEST_ROOT/scripts/cocotb/tb.$PDK.v $STEP_DIR/cocotb_rtl/tb.v
cp $TEST_ROOT/scripts/cocotb/test.py $STEP_DIR/cocotb_rtl/
cp $TEST_ROOT/scripts/cocotb/rtl.mk $STEP_DIR/cocotb_rtl/Makefile
cd $STEP_DIR/cocotb_rtl
make -B 2>&1 | tee $LOG_DIR/cocotb_rtl.log
