ROUTING_GRID = {
    "layers": {
        "Metal2": ((480, 0, 200), (420, 0, 200), "vertical"),
        "Metal3": ((480, 0, 200), (420, 0, 200), "horizontal"),
        "Metal4": ((480, 0, 200), (420, 0, 200), "vertical"),
    },
    "vias": {
        "Via2": ((210, 290), (190, 190), (290, 200)),
        "Via3": ((290, 210), (190, 190), (200, 290)),
    },
    "order": ["Metal2", "Via2", "Metal3", "Via3", "Metal4"],
    "pin_access": {
        "Metal1": {
            "vertical": [
                ("Metal2", 200, 290),
                ("Via1", 190, 190),
                ("Metal1", 210, 290),
            ],
            "horizontal": [
                ("Metal2", 200, 290),
                ("Via1", 190, 190),
                ("Metal1", 290, 210),
            ],
        },
        "Metal4": {
            "default": [("Metal4", 200, 200)],
        },
    },
}
