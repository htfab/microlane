ROUTING_GRID = {
    "layers": {
        "Metal2": ((560, 280, 280), (560, 280, 280), "vertical"),
        "Metal3": ((560, 280, 280), (560, 280, 280), "horizontal"),
        "Metal4": ((560, 280, 280), (560, 280, 280), "vertical"),
    },
    "vias": {
        "Via2": ((280, 380), (260, 260), (380, 280)),
        "Via3": ((380, 320), (260, 260), (280, 380)),
    },
    "order": ["Metal2", "Via2", "Metal3", "Via3", "Metal4"],
    "pin_access": {
        "Metal1": {
            "default": [("Metal2", 380, 280), ("Via1", 260, 260)],
        },
        "Metal4": {
            "default": [("Metal4", 280, 280)],
        },
    },
}
