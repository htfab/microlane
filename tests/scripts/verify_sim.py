#!/usr/bin/env python3

from spicelib import RawRead

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

raw = RawRead("sim.raw")

w_clk = raw.get_wave("v(clk)")
w_rst_n = raw.get_wave("v(rst_n)")
w_uo_out = [raw.get_wave(f"v(uo_out[{i}])") for i in range(8)]

clk = False
cycle = 0
for pt in range(raw.get_len()):
    negedge_clk = False
    v_clk = w_clk[pt]
    if clk:
        if v_clk < 0.6:
            clk = False
            negedge_clk = True
    else:
        if v_clk > 1.2:
            clk = True
    if not negedge_clk:
        continue
    cycle += 1
    v_rst_n = w_rst_n[pt]
    rst_n = v_rst_n > 0.9
    if cycle == 1:
        print(f"cycle {cycle}, rst_n {'high' if rst_n else 'low'}, expected high")
        assert rst_n
        continue
    elif cycle <= 6:
        print(f"cycle {cycle}, rst_n {'high' if rst_n else 'low'}, expected low")
        assert not rst_n
        continue
    assert rst_n
    v_uo_out = [w[pt] for w in w_uo_out]
    uo_out = [v > 0.9 for v in v_uo_out]
    value = sum(1 << i for i in range(8) if uo_out[i])
    if cycle == 7:
        ref = expected_output[0]
    else:
        if cycle == 8:
            refa = expected_output[1]
            refb = expected_output[0]
            if value == refa:
                delay = 6
            elif value == refb:
                delay = 7
            else:
                print(f"cycle {cycle}, value {value}, expected {refa} or {refb}")
                assert False
        ref_index = ((cycle - delay) // 2) % len(expected_output)
        ref = expected_output[ref_index]
    print(f"cycle {cycle}, value {value}, expected {ref}")
    assert value == ref

assert cycle == 100
print("simulation length ok")
