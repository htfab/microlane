# fmt: off
FLOORPLANS = {
    "1x1": {
        "die_size": (202080, 154980),
        "core_origin": (2880, 3780),
        "site_size": (480, 3780),
        "site_grid": (409, 39),
        "tap_distance_sites": 0,
        "power_nets": ["VPWR"],
        "ground_nets": ["VGND"],
        "axes": {
            "row": (20, (0, 7560)),
            "stripe": (4, (50000, 0)),
            "via": (5, (410, 0)),
            "pin": (43, (-3840, 0)),
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
            ("pr_boundary", ((0, 0), (202080, 154980)), [], "die_size"),
            ("Metal1", ((2880, 7340), (199200, 7780)), ["row"], "VPWR"),
            ("Metal1", ((2880, 3560), (199200, 4000)), ["row"], "VGND"),
            ("Via1", ((11965, 7465), (12155, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via1", ((16065, 3685), (16255, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal2", ((11960, 7415), (13800, 7705)), ["row", "stripe"], "VPWR"),
            ("Metal2", ((16060, 3635), (17900, 3925)), ["row", "stripe"], "VGND"),
            ("Via2", ((11965, 7465), (12155, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via2", ((16065, 3685), (16255, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal3", ((11915, 7460), (13845, 7660)), ["row", "stripe"], "VPWR"),
            ("Metal3", ((16015, 3680), (17945, 3880)), ["row", "stripe"], "VGND"),
            ("Via3", ((11965, 7465), (12155, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via3", ((16065, 3685), (16255, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal4", ((11830, 3560), (13930, 151420)), ["stripe"], "VPWR"),
            ("Metal4", ((15930, 3560), (18030, 151420)), ["stripe"], "VGND"),
            ("Metal4", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
            ("Metal4_pin", ((11830, 3560), (13930, 151420)), ["stripe"], "VPWR"),
            ("Metal4_pin", ((15930, 3560), (18030, 151420)), ["stripe"], "VGND"),
            ("Metal4_pin", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
        ],
        "texts": [
            ("Metal4_text", (12880, 77490), ["stripe"], "VPWR", 1.64),
            ("Metal4_text", (16980, 77490), ["stripe"], "VGND", 1.64),
            ("Metal4_text", (191040, 154480), ["pin"], "tt_pins", 0.2),
        ],
        "ports": [
            ("Metal4", (191040, 154140), ["pin"], "tt_pins", "default"),
        ],
        "lef_units_per_micron": 1000,
        "lef_ports": [
            ("Metal4", ((11830, 3560), (13930, 151420)), ["stripe"], "VPWR"),
            ("Metal4", ((15930, 3560), (18030, 151420)), ["stripe"], "VGND"),
            ("Metal4", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
        ],
        "lef_obstructions": [
            ("GatPoly", ((2880, 3630), (199200, 151350))),
            ("Metal1", ((2880, 3560), (199200, 151420))),
        ],
        "lef_bbox_obstructions": ["GatPoly", "Metal1", "Metal2", "Metal3"],
        "lef_separate_obstructions": ["Metal4"],
    }
}
# fmt: on
