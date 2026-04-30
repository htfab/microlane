def load_tech_data(pdk, scl=None):
    if pdk == "sky130A":
        if scl == "sky130_fd_sc_hd" or scl is None:
            from .sky130A.sky130_fd_sc_hd import TECH_DATA
        else:
            raise NotImplementedError(f"Unknown SCL {scl} for PDK {pdk}")
    elif pdk == "gf180mcuD":
        if scl == "gf180mcu_fd_sc_mcu7t5v0" or scl is None:
            from .gf180mcuD.gf180mcu_fd_sc_mcu7t5v0 import TECH_DATA
        else:
            raise NotImplementedError(f"Unknown SCL {scl} for PDK {pdk}")
    elif pdk == "ihp-sg13g2":
        if scl == "sg13g2_stdcell" or scl is None:
            from .ihp_sg13g2.sg13g2_stdcell import TECH_DATA
        else:
            raise NotImplementedError(f"Unknown SCL {scl} for PDK {pdk}")
    elif pdk == "ihp-sg13cmos5l":
        if scl == "sg13cmos5l_stdcell" or scl is None:
            from .ihp_sg13cmos5l.sg13cmos5l_stdcell import TECH_DATA
        else:
            raise NotImplementedError(f"Unknown SCL {scl} for PDK {pdk}")
    else:
        raise NotImplementedError(f"Unknown PDK {pdk}")
    return TECH_DATA
