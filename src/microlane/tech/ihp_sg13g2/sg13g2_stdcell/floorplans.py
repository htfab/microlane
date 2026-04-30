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
            "stripe": (5, (38870, 0)),
            "via": (5, (410, 0)),
            "topvia": (2, (840, 0)),
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
            ("Via1", ((15565, 7465), (15755, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via1", ((21765, 3685), (21955, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal2", ((15560, 7415), (17400, 7705)), ["row", "stripe"], "VPWR"),
            ("Metal2", ((21760, 3635), (23600, 3925)), ["row", "stripe"], "VGND"),
            ("Via2", ((15565, 7465), (15755, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via2", ((21765, 3685), (21955, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal3", ((15515, 7460), (17445, 7660)), ["row", "stripe"], "VPWR"),
            ("Metal3", ((21715, 3680), (23645, 3880)), ["row", "stripe"], "VGND"),
            ("Via3", ((15565, 7465), (15755, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via3", ((21765, 3685), (21955, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal4", ((15560, 7415), (17400, 7705)), ["row", "stripe"], "VPWR"),
            ("Metal4", ((21760, 3635), (23600, 3925)), ["row", "stripe"], "VGND"),
            ("Via4", ((15565, 7465), (15755, 7655)), ["row", "stripe", "via"], "VPWR"),
            ("Via4", ((21765, 3685), (21955, 3875)), ["row", "stripe", "via"], "VGND"),
            ("Metal5", ((15515, 7250), (17445, 7870)), ["row", "stripe"], "VPWR"),
            ("Metal5", ((21715, 3470), (23645, 4090)), ["row", "stripe"], "VGND"),
            ("TopVia1", ((15850, 7350), (16270, 7770)), ["row", "stripe", "topvia"], "VPWR"),
            ("TopVia1", ((22050, 3570), (22470, 3990)), ["row", "stripe", "topvia"], "VGND"),
            ("TopMetal1", ((15380, 3560), (17580, 151830)), ["stripe"], "VPWR"),
            ("TopMetal1", ((21580, 3150), (23780, 151420)), ["stripe"], "VGND"),
            ("Metal4", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
            ("TopMetal1_pin", ((15380, 3560), (17580, 151830)), ["stripe"], "VPWR"),
            ("TopMetal1_pin", ((21580, 3150), (23780, 151420)), ["stripe"], "VGND"),
            ("Metal4_pin", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
        ],
        "texts": [
            ("TopMetal1_text", (16480, 77695), ["stripe"], "VPWR", 1.64),
            ("TopMetal1_text", (22680, 77285), ["stripe"], "VGND", 1.64),
            ("Metal4_text", (191040, 154480), ["pin"], "tt_pins", 0.2),
        ],
        "ports": [
            ("Metal4", (191040, 154140), ["pin"], "tt_pins", "default"),
        ],
        "lef_units_per_micron": 1000,
        "lef_ports": [
            ("TopMetal1", ((15380, 3560), (17580, 151830)), ["stripe"], "VPWR"),
            ("TopMetal1", ((21580, 3150), (23780, 151420)), ["stripe"], "VGND"),
            ("Metal4", ((190890, 153980), (191190, 154980)), ["pin"], "tt_pins"),
        ],
        "lef_obstructions": [
            ("GatPoly", ((2880, 3630), (199200, 151350))),
            ("Metal1", ((2880, 3560), (199200, 151420))),
        ],
        "lef_bbox_obstructions": ["GatPoly", "Metal1", "Metal2", "Metal3", "Metal5"],
        "lef_separate_obstructions": ["Metal4", "TopMetal1"],
    }
}
# fmt: on
