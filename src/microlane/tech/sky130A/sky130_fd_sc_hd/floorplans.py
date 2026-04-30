# fmt: off
FLOORPLANS = {
    "1x1": {
        "die_size": (161000, 111520),
        "core_origin": (2760, 2720),
        "site_size": (460, 2720),
        "site_grid": (338, 39),
        "tap_distance_sites": 28,
        "power_nets": ["VPWR"],
        "ground_nets": ["VGND"],
        "axes": {
            "row": (20, (0, 5440)),
            "stripe": (4, (38870, 0)),
            "via1": (5, (320, 0)),
            "via23": (4, (400, 0)),
            "pin": (43, (-2760, 0)),
        },
        "lists": {
            "tt_pins": (
                ["ena", "clk", "rst_n"]
                + [
                    f"{port}[{i}]"
                    for port in ("ui_in", "uio_in", "uo_out", "uio_out", "uio_oe")
                    for i in range(8)
                ]
            ),
        },
        "rects": [
            ("pr_boundary", ((0, 0), (161000, 111520)), [], "die_size"),
            ("met1", ((2760, 5200), (158240, 5680)), ["row"], "VPWR"),
            ("met1", ((2760, 2480), (158240, 2960)), ["row"], "VGND"),
            ("via1", ((18365, 5365), (18515, 5515)), ["row", "stripe", "via1"], "VPWR"),
            ("via1", ((21665, 2645), (21815, 2795)), ["row", "stripe", "via1"], "VGND"),
            ("met2", ((18310, 5255), (19850, 5625)), ["row", "stripe"], "VPWR"),
            ("met2", ((21610, 2535), (23150, 2905)), ["row", "stripe"], "VGND"),
            ("via2", ((18380, 5340), (18580, 5540)), ["row", "stripe", "via23"], "VPWR"),
            ("via2", ((21680, 2620), (21880, 2820)), ["row", "stripe", "via23"], "VGND"),
            ("met3", ((18290, 5275), (19870, 5605)), ["row", "stripe"], "VPWR"),
            ("met3", ((21590, 2555), (23170, 2885)), ["row", "stripe"], "VGND"),
            ("via3", ((18380, 5340), (18580, 5540)), ["row", "stripe", "via23"], "VPWR"),
            ("via3", ((21680, 2620), (21880, 2820)), ["row", "stripe", "via23"], "VGND"),
            ("met4", ((18280, 2480), (19880, 109040)), ["stripe"], "VPWR"),
            ("met4", ((21580, 2480), (23180, 109040)), ["stripe"], "VGND"),
            ("met4", ((146590, 110520), (146890, 111520)), ["pin"], "tt_pins"),
            ("met4_pin", ((18280, 2480), (19880, 109040)), ["stripe"], "VPWR"),
            ("met4_pin", ((21580, 2480), (23180, 109040)), ["stripe"], "VGND"),
            ("met4_pin", ((146590, 110520), (146890, 111520)), ["pin"], "tt_pins"),
        ],
        "texts": [
            ("met4_label", (19080, 55760), ["stripe"], "VPWR", 1.2),
            ("met4_label", (22380, 55760), ["stripe"], "VGND", 1.2),
            ("met4_label", (146740, 111020), ["pin"], "tt_pins", 0.3),
        ],
        "ports": [
            ("met4", (146740, 110860), ["pin"], "tt_pins", "default"),
        ],
        "lef_units_per_micron": 1000,
        "lef_ports": [
            ("met4", ((18280, 2480), (19880, 109040)), ["stripe"], "VPWR"),
            ("met4", ((21580, 2480), (23180, 109040)), ["stripe"], "VGND"),
            ("met4", ((146590, 110520), (146890, 111520)), ["pin"], "tt_pins"),
        ],
        "lef_obstructions": [
            ("nwell", ((2570, 2635), (158430, 108990))),
            ("li1", ((2760, 2635), (158240, 108885))),
            ("met1", ((2760, 2480), (158240, 109040))),
        ],
        "lef_bbox_obstructions": ["nwell", "li1", "met1", "met2", "met3"],
        "lef_separate_obstructions": ["met4"],
    }
}
# fmt: on
