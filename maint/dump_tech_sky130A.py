#!/usr/bin/env python3

import os

from microlane.util.gds import GdsLibrary, GdsWriter

pdk_dir = os.environ["PDK_ROOT"]
pdk = "sky130A"
scl = "sky130_fd_sc_hd"
output_dir = f"../src/microlane/tech/{pdk}/{scl}"

cells = [
    ("sky130_fd_sc_hd__buf_1", ["logic"]),
    ("sky130_fd_sc_hd__inv_1", ["logic"]),
    ("sky130_fd_sc_hd__and2_1", ["logic"]),
    ("sky130_fd_sc_hd__and2b_1", ["logic"]),
    ("sky130_fd_sc_hd__nand2_1", ["logic"]),
    ("sky130_fd_sc_hd__or2_1", ["logic"]),
    ("sky130_fd_sc_hd__or2b_1", ["logic"]),
    ("sky130_fd_sc_hd__nor2_1", ["logic"]),
    ("sky130_fd_sc_hd__xor2_1", ["logic"]),
    ("sky130_fd_sc_hd__xnor2_1", ["logic"]),
    ("sky130_fd_sc_hd__mux2_1", ["logic"]),
    ("sky130_fd_sc_hd__ha_1", ["logic"]),
    ("sky130_fd_sc_hd__fa_1", ["logic"]),
    ("sky130_fd_sc_hd__conb_1", ["logic"]),
    ("sky130_fd_sc_hd__dfxtp_1", ["logic"]),
    ("sky130_fd_sc_hd__dlxtp_1", ["logic"]),
    ("sky130_fd_sc_hd__dlclkp_1", ["logic"]),
    ("sky130_fd_sc_hd__fill_1", ["fill"]),
    ("sky130_fd_sc_hd__fill_2", ["fill"]),
    ("sky130_fd_sc_hd__decap_3", ["fill", "endcap"]),
    ("sky130_fd_sc_hd__decap_4", ["fill"]),
    ("sky130_fd_sc_hd__decap_6", ["fill"]),
    ("sky130_fd_sc_hd__decap_8", ["fill"]),
    ("sky130_ef_sc_hd__decap_12", ["fill"]),
    ("sky130_fd_sc_hd__tapvpwrvgnd_1", ["tap"]),
]

met1_blockages = {
    "sky130_fd_sc_hd__fa_1": [
        (1545, 780, 5385, 920),
        (1470, 735, 1760, 965),
        (5170, 735, 5460, 965),
        (1085, 1120, 6305, 1260),
        (1010, 1075, 1300, 1305),
        (2390, 1075, 2680, 1305),
        (4250, 1075, 4540, 1305),
        (6090, 1075, 6380, 1305),
        (1545, 1460, 5845, 1600),
        (1470, 1415, 1760, 1645),
        (3330, 1415, 3620, 1645),
        (5630, 1415, 5920, 1645),
    ],
    "sky130_fd_sc_hd__dfxtp_1": [
        (1040, 1460, 4890, 1600),
        (965, 1415, 1255, 1645),
        (2155, 1415, 2445, 1645),
        (4675, 1415, 4965, 1645),
        (645, 1800, 4455, 1940),
        (570, 1755, 860, 1985),
        (2670, 1755, 2960, 1985),
        (4240, 1755, 4530, 1985),
    ],
    "sky130_fd_sc_hd__dlxtp_1": [
        (625, 1460, 2625, 1600),
        (550, 1415, 840, 1645),
        (2410, 1415, 2700, 1645),
        (1085, 1800, 3085, 1940),
        (1010, 1755, 1300, 1985),
        (2870, 1755, 3160, 1985),
    ],
    "sky130_fd_sc_hd__dlclkp_1": [
        (160, 1120, 5365, 1260),
        (85, 1075, 380, 1305),
        (5150, 1075, 5440, 1305),
    ],
}

pdk_dir = os.path.join(os.path.dirname(__file__), pdk_dir)

roles = dict(cells)
mags = {}
for cell, _ in cells:
    mags[cell] = f"{pdk_dir}/{pdk}/libs.ref/{scl}/mag/{cell}.mag"

with open(f"{output_dir}/std_cells.py", "w") as f:
    f.write("STD_CELLS = {\n")
    for cell, mag in mags.items():
        pins = {}
        boundary = []
        inputs = set()
        outputs = set()
        with open(mag) as g:
            label = None
            for line in g:
                last_label = label
                label = None
                if line.startswith("flabel "):
                    _, layer, _, x1, y1, x2, y2, _, _, _, _, _, _, label = (
                        line.strip().split(" ")
                    )
                    if label in ("VPWR", "VGND", "VNB", "VPB"):
                        continue
                    if layer == "comment":
                        continue
                    assert layer == "locali"
                    cl = "li1"
                    x1, y1, x2, y2 = (int(t) * 5 for t in (x1, y1, x2, y2))
                    assert (x1 + x2) % 2 == 0
                    assert (y1 + y2) % 2 == 0
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    if cell == "sky130_fd_sc_hd__conb_1" and label == "HI":
                        # override off-grid pin
                        assert cy == 1210
                        cy = 1190
                    elif cell == "sky130_fd_sc_hd__dlclkp_1" and label == "CLK":
                        # move hard-to-access pin
                        assert (cl, cx, cy) == ("li1", 235, 1530)
                        cl, cx, cy = "met1", 230, 1190
                    assert cy % 340 == 170
                    ca = "default"
                    pins.setdefault(label, []).append((cl, cx, cy, ca))
                elif line.startswith("port "):
                    if last_label is not None:
                        port_args = line.strip().split(" ")
                        if len(port_args) > 4:
                            direction = port_args[4]
                            if direction == "input":
                                inputs.add(last_label)
                            if direction == "output":
                                outputs.add(last_label)
                elif line.startswith("string FIXED_BBOX "):
                    _, _, x1, y1, x2, y2 = line.strip().split(" ")
                    x1, y1, x2, y2 = (int(t) * 5 for t in (x1, y1, x2, y2))
                    boundary.append((x1, y1, x2, y2))
        assert len(boundary) == 1
        boundary = boundary[0]
        x1, y1, x2, y2 = boundary
        assert x1 == y1 == 0
        assert x2 % 460 == 0
        assert y2 % 2720 == 0
        sites = (x2 // 460, y2 // 2720)
        blockages = []
        for blockage in met1_blockages.get(cell, []):
            blockages.append(("met1", *blockage))
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
