def load_tech_data(tech):
    if tech == "sky130_fd_sc_hd":
        from .sky130_fd_sc_hd import TECH_DATA
    else:
        raise NotImplementedError(f"Unknown technology: {tech}")
    return TECH_DATA
