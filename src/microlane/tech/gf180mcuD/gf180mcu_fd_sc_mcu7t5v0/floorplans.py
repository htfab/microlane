# fmt: off
FLOORPLANS = {
    "1x1": {
        "die_size": (346640, 160720),
        "core_origin": (3360, 3920),
        "site_size": (560, 3920),
        "site_grid": (607, 39),
        "tap_distance_sites": 35,
        "power_nets": ["VPWR"],
        "ground_nets": ["VGND"],
        "axes": {
            "row": (20, (0, 7840)),
            "stripe": (9, (38870, 0)),
            "via": (3, (520, 0)),
            "pin": (43, (-7280, 0)),
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
            ("PR_bndry", ((0, 0), (346640, 160720)), [], "die_size"),
            ("Metal1", ((3360, 7540), (343280, 8140)), ["row"], "VPWR"),
            ("Metal1", ((3360, 3620), (343280, 4220)), ["row"], "VGND"),
            ("Via1", ((19030, 7710), (19290, 7970)), ["row", "stripe", "via"], "VPWR"),
            ("Via1", ((22330, 3790), (22590, 4050)), ["row", "stripe", "via"], "VGND"),
            ("Metal2", ((19020, 7650), (20340, 8030)), ["row", "stripe"], "VPWR"),
            ("Metal2", ((22320, 3730), (23640, 4110)), ["row", "stripe"], "VGND"),
            ("Via2", ((19030, 7710), (19290, 7970)), ["row", "stripe", "via"], "VPWR"),
            ("Via2", ((22330, 3790), (22590, 4050)), ["row", "stripe", "via"], "VGND"),
            ("Metal3", ((18970, 7700), (20390, 7980)), ["row", "stripe"], "VPWR"),
            ("Metal3", ((22270, 3780), (23690, 4060)), ["row", "stripe"], "VGND"),
            ("Via3", ((19030, 7710), (19290, 7970)), ["row", "stripe", "via"], "VPWR"),
            ("Via3", ((22330, 3790), (22590, 4050)), ["row", "stripe", "via"], "VGND"),
            ("Metal4", ((18880, 3620), (20480, 157100)), ["stripe"], "VPWR"),
            ("Metal4", ((22180, 3620), (23780, 157100)), ["stripe"], "VGND"),
            ("Metal4", ((338370, 159460), (338670, 160720)), ["pin"], "tt_pins"),
        ],
        "texts": [
            ("Metal4_Label", (19680, 80360), ["stripe"], "VPWR", 0.92),
            ("Metal4_Label", (22980, 80360), ["stripe"], "VGND", 0.92),
            ("Metal4_Label", (338520, 160220), ["pin"], "tt_pins", 0.23),
        ],
        "ports": [
            ("Metal4", (338520, 159320), ["pin"], "tt_pins", "default"),
        ],
        "lef_units_per_micron": 1000,
        "lef_ports": [
            ("Metal4", ((18880, 3620), (20480, 157100)), ["stripe"], "VPWR"),
            ("Metal4", ((22180, 3620), (23780, 157100)), ["stripe"], "VGND"),
            ("Metal4", ((338370, 159720), (338670, 160720)), ["pin"], "tt_pins"),
        ],
        "lef_obstructions": [
            ("Nwell", ((2930, 3490), (343710, 157230))),
            ("Pwell", ((2930, 3490), (343710, 157230))),
            ("Metal1", ((3360, 3620), (343280, 157100))),
        ],
        "lef_bbox_obstructions": ["Nwell", "Pwell", "Metal1", "Metal2", "Metal3"],
        "lef_separate_obstructions": ["Metal4"],
    }
}
# fmt: on
