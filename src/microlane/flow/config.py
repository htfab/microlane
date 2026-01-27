DEFAULT_CONFIG = {
    # global
    "pdk": "sky130",
    "pdk_variant": "sky130A",
    "std_cell_library": "sky130_fd_sc_hd",
    "template": "1x1",
    "show_progress": True,
    "project_name": None,
    "source_files": ["project.v"],
    "run_dir": ".",
    # debug
    "debug.dump_synth_trees": False,
    "debug.skip_routing": False,
    "debug.verbose_routing": False,
    "debug.air_wires_in_gds": False,
    "debug.blockages_in_gds": False,
    # bit blaster
    "synth.split_mux": False,
    "synth.split_half_adder": False,
    "synth.split_full_adder": False,
    # elaborator
    "synth.loop_unroll_max": 100,
    "synth.logic_chain_max": 100,
    # cleaner
    "synth.cleanup_steps_max": 100,
    # clock splitter
    "synth.split_clock": True,
    "synth.clock_net": "clk",
    "synth.reset_n_net": "rst_n",
    # bufferer
    "synth.max_fanout": 10,
    # placement
    "placement.random_seed": 0,
    "placement.init_temperature": 1000,
    "placement.cooling_factor": 0.9,
    "placement.updates_per_gate": 100,
    "placement.extra_space_x": 4,
    "placement.extra_space_y": 1,
    # routing
    "routing.wrong_direction_multiplier": 5,
    "routing.layer_multiplier": {"met1": 1, "met2": 1, "met3": 2, "met4": 2},
    "routing.via_penalty": 6800,  # equivalent wire length in nm
    "routing.access_penalty": (
        100000,
        25000,
        12500,
        8000,
    ),
    "routing.pdn_extra_blockage": 0,
    "routing.std_cell_extra_blockage": 0,
}
