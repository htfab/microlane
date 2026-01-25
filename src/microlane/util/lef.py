class LefWriter:
    def __init__(self, path, db_units_per_micron):
        self.path = path
        self.div = db_units_per_micron

    def __enter__(self):
        self.file = open(self.path, "w")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()

    def write_file_header(self):
        self.file.write("VERSION 5.7 ;\n")
        self.file.write("  NOWIREEXTENSIONATPIN ON ;\n")
        self.file.write('  DIVIDERCHAR "/" ;\n')
        self.file.write('  BUSBITCHARS "[]" ;\n')

    def write_file_footer(self):
        self.file.write("END LIBRARY\n")
        self.file.write("\n")

    def write_macro_header(self, name, width, height):
        width /= self.div
        height /= self.div
        self.file.write(f"MACRO {name}\n")
        self.file.write("  CLASS BLOCK ;\n")
        self.file.write(f"  FOREIGN {name} ;\n")
        self.file.write("  ORIGIN 0.000 0.000 ;\n")
        self.file.write(f"  SIZE {width:.3f} BY {height:.3f} ;\n")

    def write_macro_footer(self, name):
        self.file.write(f"END {name}\n")

    def write_pin_header(self, name, direction, use, gate_area=None, diff_area=None):
        self.file.write(f"  PIN {name}\n")
        self.file.write(f"    DIRECTION {direction.upper()} ;\n")
        self.file.write(f"    USE {use.upper()} ;\n")
        if diff_area is not None:
            diff_area /= self.div**2
            self.file.write(f"    ANTENNADIFFAREA {diff_area:.6f} ;\n")
        if gate_area is not None:
            gate_area /= self.div**2
            self.file.write(f"    ANTENNAGATEAREA {gate_area:.6f} ;\n")

    def write_pin_footer(self, name):
        self.file.write(f"  END {name}\n")

    def write_port_header(self):
        self.file.write("    PORT\n")

    def write_port_footer(self):
        self.file.write("    END\n")

    def write_obs_header(self):
        self.file.write("  OBS\n")

    def write_obs_footer(self):
        self.file.write("  END\n")

    def write_layer_entry(self, layer):
        self.file.write(f"      LAYER {layer} ;\n")

    def write_rect_entry(self, x1, y1, x2, y2):
        x1 /= self.div
        y1 /= self.div
        x2 /= self.div
        y2 /= self.div
        self.file.write(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;\n")
