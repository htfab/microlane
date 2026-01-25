# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

expected_output = [
    0b01110100,
    0b01110111,
    0b01010000,
    0b01011110,
    0b01111001,
    0b01010100,
    0b01111001,
    0b01011110,
    0b00000000,
    0b00111110,
    0b01101101,
    0b00110000,
    0b01010100,
    0b00111101,
    0b00000000,
    0b01110011,
    0b01101110,
    0b01111000,
    0b01110100,
    0b01011100,
    0b01010100,
    0b00000000,
]


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    gl_test = "GATES" in os.environ
    clock_multiplier = 2 if gl_test else 1

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    dut._log.info("Test project behavior")

    for eo in expected_output * 3:
        await ClockCycles(dut.clk, clock_multiplier)
        assert dut.uo_out.value == eo
