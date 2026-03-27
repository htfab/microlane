#!/bin/bash
echo '======================'
echo 'running test cocotb_gl'
echo '======================'
if [ -z "$PDK" ]; then
    echo "PDK is unset" && exit 1
fi
if [ "$PDK" == "sky130A" ]; then
    export USE_PNL=1
elif [ "$PDK" == "ihp-sg13g2" ]; then
    export USE_PNL=0
elif [ "$PDK" == "ihp-sg13cmos5l" ]; then
    export USE_PNL=0
else
    echo "Unknown PDK" && exit 1
fi
export TEST_ROOT=$(dirname $(realpath $0))
export STEP_DIR=$TEST_ROOT/outputs/$PDK
export LOG_DIR=$TEST_ROOT/logs/$PDK
rm -rf $STEP_DIR/cocotb_gl $LOG_DIR/cocotb_gl.log
mkdir -p $STEP_DIR/cocotb_gl
mkdir -p $LOG_DIR
if [ $USE_PNL -eq 1 ]; then
    cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.pnl.v $STEP_DIR/cocotb_gl/gate_level_netlist.v
else
    cp $STEP_DIR/harden_cmdline/tt_um_microlane_demo.nl.v $STEP_DIR/cocotb_gl/gate_level_netlist.v
fi
cp $TEST_ROOT/scripts/cocotb/tb.$PDK.v $STEP_DIR/cocotb_gl/tb.v
cp $TEST_ROOT/scripts/cocotb/test.py $STEP_DIR/cocotb_gl/test.py
cp $TEST_ROOT/scripts/cocotb/gl.$PDK.mk $STEP_DIR/cocotb_gl/Makefile
cd $STEP_DIR/cocotb_gl
GATES=yes make -B 2>&1 | tee $LOG_DIR/cocotb_gl.log
