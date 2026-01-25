from .floorplans import FLOORPLANS
from .layers import LAYERS
from .pdk_info import PDK_INFO
from .pnl_terminals import PNL_TERMINALS
from .routing_grid import ROUTING_GRID
from .rules import RULES
from .std_cells import STD_CELLS
from .tech_map import TECH_MAP

try:
    from importlib.resources import files

    std_cells_gds = files(__name__).joinpath("std_cells.gds")
    del files
except ImportError:
    std_cells_gds = __file__.rsplit("/", 1)[0] + "/std_cells.gds"

TECH_DATA = {
    "pdk_info": PDK_INFO,
    "tech_map": TECH_MAP,
    "pnl_terminals": PNL_TERMINALS,
    "layers": LAYERS,
    "routing_grid": ROUTING_GRID,
    "rules": RULES,
    "floorplans": FLOORPLANS,
    "std_cells": STD_CELLS,
    "std_cells_gds": std_cells_gds,
}
