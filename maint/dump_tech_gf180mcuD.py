#!/usr/bin/env python3

import os
from decimal import Decimal

from microlane.util.gds import GdsLibrary, GdsWriter

pdk_dir = os.environ["PDK_ROOT"]
pdk = "gf180mcuD"
scl = "gf180mcu_fd_sc_mcu7t5v0"
output_dir = f"../src/microlane/tech/{pdk}/{scl}"

cells = [
    ("gf180mcu_fd_sc_mcu7t5v0__buf_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__inv_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__and2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__nand2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__or2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__nor2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__xor2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__xnor2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__mux2_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__addh_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__addf_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__tiel", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__tieh", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__dffq_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__latq_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__icgtp_1", ["logic"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fill_1", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fill_2", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fillcap_4", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fillcap_8", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fillcap_16", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fillcap_32", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__fillcap_64", ["fill"]),
    ("gf180mcu_fd_sc_mcu7t5v0__endcap", ["endcap"]),
    ("gf180mcu_fd_sc_mcu7t5v0__filltie", ["tap"]),
]

pdk_dir = os.path.join(os.path.dirname(__file__), pdk_dir)

roles = dict(cells)

cell_data = {}
with open(f"{pdk_dir}/{pdk}/libs.ref/{scl}/lef/{scl}.lef") as f:
    current_cell = None
    for line in f:
        line = line.removesuffix("\n")
        if line.startswith("MACRO "):
            current_cell = line.removeprefix("MACRO ").strip()
            boundary = []
            inputs = set()
            outputs = set()
            pin_rects = {}
            obstructions = []
            current_pin = None
            in_port = False
            in_obs = False
        elif current_cell is None:
            continue
        elif current_cell not in roles:
            continue
        elif line.startswith("END "):
            assert current_cell not in cell_data
            assert len(boundary) == 1
            cell_data[current_cell] = {
                "boundary": boundary[0],
                "inputs": inputs,
                "outputs": outputs,
                "pin_rects": pin_rects,
                "obstructions": obstructions,
            }
            current_cell = None
        elif line.startswith("  SIZE "):
            width, _, height, *_ = line.removeprefix("  SIZE ").strip().split()
            width = Decimal(width) * 1000
            height = Decimal(height) * 1000
            assert width == int(width)
            assert height == int(height)
            width, height = int(width), int(height)
            boundary.append((0, 0, width, height))
        elif line == "  OBS":
            assert not in_obs
            in_obs = True
        elif line == "  END":
            assert in_obs
            in_obs = False
        elif line.startswith("    LAYER "):
            assert in_obs
            current_layer = line.removeprefix("    LAYER ").strip().split()[0]
        elif line.startswith("      RECT "):
            assert in_obs
            assert current_layer is not None
            x1, y1, x2, y2, *_ = line.removeprefix("      RECT ").strip().split()
            x1, y1, x2, y2 = (Decimal(i) * 1000 for i in (x1, y1, x2, y2))
            assert all(i == int(i) for i in (x1, y1, x2, y2))
            x1, y1, x2, y2 = (int(i) for i in (x1, y1, x2, y2))
            obstructions.append((current_layer, x1, y1, x2, y2))
        elif line.startswith("  PIN "):
            current_pin = line.removeprefix("  PIN ").strip()
            if current_pin in ("VDD", "VSS", "VNW", "VPW"):
                current_pin = None
                continue
            in_port = False
        elif current_pin is None:
            continue
        elif line.startswith("  END "):
            current_pin = None
        elif line.startswith("    DIRECTION "):
            direction = line.removeprefix("    DIRECTION ").strip().split()[0]
            if direction == "INPUT":
                inputs.add(current_pin)
            elif direction == "OUTPUT":
                outputs.add(current_pin)
        elif line == "    PORT":
            assert not in_port
            in_port = True
            current_layer = None
        elif line == "    END":
            assert in_port
            in_port = False
        elif line.startswith("      LAYER "):
            assert in_port
            current_layer = line.removeprefix("      LAYER ").strip().split()[0]
        elif line.startswith("        RECT "):
            assert in_port
            assert current_layer is not None
            x1, y1, x2, y2, *_ = line.removeprefix("        RECT ").strip().split()
            x1, y1, x2, y2 = (Decimal(i) * 1000 for i in (x1, y1, x2, y2))
            assert all(i == int(i) for i in (x1, y1, x2, y2))
            x1, y1, x2, y2 = (int(i) for i in (x1, y1, x2, y2))
            pin_rects.setdefault(current_pin, []).append(
                (current_layer, x1, y1, x2, y2)
            )


with open(f"{output_dir}/std_cells.py", "w") as f:
    f.write("STD_CELLS = {\n")
    for cell, cell_roles in cells:
        cd = cell_data[cell]
        boundary = cd["boundary"]
        x1, y1, x2, y2 = boundary
        assert x1 == y1 == 0
        assert x2 % 560 == 0
        assert y2 % 3920 == 0
        sites = (x2 // 560, y2 // 3920)
        inputs = cd["inputs"]
        outputs = cd["outputs"]
        pin_rects = cd["pin_rects"]
        obstructions = cd["obstructions"]

        pins = {}
        for pin, pr in sorted(pin_rects.items()):
            pins[pin] = set()
            for layer, x1, y1, x2, y2 in pr:
                xr = range((x1 // 560) * 560 + 280, x2, 560)
                xd = [x for x in xr if x1 + 130 <= x <= x2 - 130]
                yr = range((y1 // 560) * 560 + 280, y2, 560)
                yd = [y for y in yr if y1 + 130 <= y <= y2 - 130]
                for y in yd:
                    for x in xd:
                        pins[pin].add((layer, x, y, "default"))
            if not pins[pin]:
                # manual overrides
                if cell == "sg13cmos5l_or2_1" and pin == "B":
                    pins[pin] = {("Metal1", 960, 2520, "vertical")}
                elif cell == "sg13cmos5l_xor2_1" and pin == "X":
                    pins[pin] = {("Metal1", 2880, 840, "vertical")}
                else:
                    print(f"Error: no grid points for pin {cell}.{pin}")
            pins[pin] = sorted(pins[pin])

        blockages = []

        f.write(f'    "{cell}": {{\n')
        roles_str = "[" + ", ".join(f'"{i}"' for i in roles[cell]) + "]"
        f.write(f'        "roles": {roles_str},\n')
        f.write(f'        "sites": {sites},\n')
        f.write(f'        "boundary": {boundary},\n')
        inputs_str = "[" + ", ".join(f'"{i}"' for i in sorted(inputs)) + "]"
        f.write(f'        "inputs": {inputs_str},\n')
        outputs_str = "[" + ", ".join(f'"{i}"' for i in sorted(outputs)) + "]"
        f.write(f'        "outputs": {outputs_str},\n')
        if pins:
            f.write('        "pins": {\n')
            for k, v in sorted(pins.items()):
                v_s = [f'("{vl}", {vx}, {vy}, "{va}")' for vl, vx, vy, va in v]
                v_c = "[" + ", ".join(v_s) + "]"
                if len(v_c) < 68:
                    f.write(f'            "{k}": {v_c},\n')
                else:
                    f.write(f'            "{k}": [\n')
                    for v_e in v_s:
                        f.write(f"                {v_e},\n")
                    f.write("            ],\n")
            f.write("        },\n")
        else:
            f.write('        "pins": {},\n')
        if blockages:
            f.write('        "blockages": [\n')
            for bl, bx1, by1, bx2, by2 in blockages:
                b_str = f'("{bl}", {bx1}, {by1}, {bx2}, {by2})'
                f.write(f"            {b_str},\n")
            f.write("        ],\n")
        else:
            f.write('        "blockages": [],\n')
        f.write("    },\n")
    f.write("}\n")

with GdsLibrary(f"{pdk_dir}/{pdk}/libs.ref/{scl}/gds/{scl}.gds") as gl:
    with GdsWriter(f"{output_dir}/std_cells.gds") as gw:
        gw.write_header(scl)
        for cell, _ in cells:
            gw.stream_from_library(gl.get_cell(cell))
        gw.write_footer()
