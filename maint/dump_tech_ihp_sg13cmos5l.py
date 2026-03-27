#!/usr/bin/env python3

import os
from decimal import Decimal

from microlane.util.gds import GdsLibrary, GdsWriter

pdk_dir = os.environ["PDK_ROOT"]
pdk = "ihp-sg13cmos5l"
scl = "sg13cmos5l_stdcell"
output_dir = f"../src/microlane/tech/{pdk.replace('-', '_')}/{scl}"

cells = [
    ("sg13cmos5l_and2_1", ["logic"]),
    ("sg13cmos5l_buf_1", ["logic"]),
    ("sg13cmos5l_dfrbpq_1", ["logic"]),
    ("sg13cmos5l_dlhq_1", ["logic"]),
    ("sg13cmos5l_inv_1", ["logic"]),
    ("sg13cmos5l_lgcp_1", ["logic"]),
    ("sg13cmos5l_mux2_1", ["logic"]),
    ("sg13cmos5l_nand2_1", ["logic"]),
    ("sg13cmos5l_nand2b_1", ["logic"]),
    ("sg13cmos5l_nor2_1", ["logic"]),
    ("sg13cmos5l_nor2b_1", ["logic"]),
    ("sg13cmos5l_or2_1", ["logic"]),
    ("sg13cmos5l_tiehi", ["logic"]),
    ("sg13cmos5l_tielo", ["logic"]),
    ("sg13cmos5l_xnor2_1", ["logic"]),
    ("sg13cmos5l_xor2_1", ["logic"]),
    ("sg13cmos5l_fill_1", ["fill"]),
    ("sg13cmos5l_fill_2", ["fill"]),
    ("sg13cmos5l_decap_4", ["fill"]),
    ("sg13cmos5l_decap_8", ["fill"]),
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
            if current_pin in ("VDD", "VSS"):
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
        assert x2 % 480 == 0
        assert y2 % 3780 == 0
        sites = (x2 // 480, y2 // 3780)
        inputs = cd["inputs"]
        outputs = cd["outputs"]
        pin_rects = cd["pin_rects"]
        obstructions = cd["obstructions"]

        pins = {}
        for pin, pr in sorted(pin_rects.items()):
            pins[pin] = set()
            for layer, x1, y1, x2, y2 in pr:
                xr = range((x1 // 480) * 480, x2, 480)
                xv = [x for x in xr if x1 + 105 <= x <= x2 - 105]
                xh = [x for x in xr if x1 + 145 <= x <= x2 - 145]
                yr = range((y1 // 420) * 420, y2, 420)
                yv = [y for y in yr if y1 + 145 <= y <= y2 - 145]
                yh = [y for y in yr if y1 + 105 <= y <= y2 - 105]
                for y in yv:
                    for x in xv:
                        pins[pin].add((layer, x, y, "vertical"))
                for y in yh:
                    for x in xh:
                        pins[pin].add((layer, x, y, "horizontal"))
            if not pins[pin]:
                # manual overrides
                if cell == "sg13cmos5l_or2_1" and pin == "B":
                    pins[pin] = {("Metal1", 960, 2520, "vertical")}
                elif cell == "sg13cmos5l_xor2_1" and pin == "X":
                    pins[pin] = {("Metal1", 2880, 840, "vertical")}
                else:
                    print(f"Error: no grid points for pin {cell}.{pin}")
            for layer, x, y, access_type in sorted(pins[pin]):
                if access_type == "vertical":
                    pins[pin].discard((layer, x, y, "horizontal"))
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
