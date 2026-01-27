from ..util import progress
from ..util.gds import GdsLibrary, GdsWriter
from ..util.lef import LefWriter


def gds_streamout(layout, gds):
    progress.step("Writing GDS", 1)
    air_wires_in_gds = layout.config["debug.air_wires_in_gds"]
    output_name = "top" if layout.name is None else layout.name
    layers = layout.config["tech"]["layers"]
    cell_gds = layout.config["tech"]["std_cells_gds"]
    sw, sh = layout.floorplan.site_size
    with GdsLibrary(cell_gds) as gl:
        with GdsWriter(gds) as gw:
            gw.write_header(output_name)
            for cell in sorted(set(inst.cell for inst in layout.instances)):
                gw.stream_from_library(gl.get_cell(cell))
            gw.start_cell(output_name)
            for inst in layout.instances:
                if inst.placement is not None:
                    if inst.placement.status != "UNPLACED":
                        assert inst.placement.orient in ("N", "S", "FN", "FS")
                        flip = inst.placement.orient in ("S", "FN")
                        flop = inst.placement.orient in ("S", "FS")
                        dx, dy = 0, 0
                        cw, ch = layout.cell_data[inst.cell].sites
                        if flip:
                            dx += cw * sw
                        if flop:
                            dy += ch * sh
                        gw.add_instance(
                            inst.cell,
                            inst.name,
                            inst.placement.x + dx,
                            inst.placement.y + dy,
                            flip=flip,
                            flop=flop,
                        )
            gw.add_rect(*layers["pr_boundary"], (0, 0), layout.floorplan.die_size)
            for rect, layer, label, _ in layout.floorplan.resolve_rects():
                gw.add_rect(*layers[layer], (rect.x1, rect.y1), (rect.x2, rect.y2))
            for point, layer, label, label_size in layout.floorplan.resolve_texts():
                gw.add_text(*layers[layer], (point.x, point.y), label, label_size, 90)
            if layout.rects is not None:
                for net, layer, rect in layout.rects:
                    gw.add_rect(*layers[layer], (rect.x1, rect.y1), (rect.x2, rect.y2))
            if air_wires_in_gds:
                if layout.air_wires is not None:
                    for air_wire in layout.air_wires:
                        layer, polygon = air_wire.as_polygon()
                        gw.add_polygon(*layers[layer], polygon)
            gw.end_cell()
            gw.write_footer()


def lef_streamout(layout, lef):
    progress.step("Writing LEF", 1)
    macro_name = "top" if layout.name is None else layout.name
    die_size_x, die_size_y = layout.floorplan.die_size
    db_units_per_micron = layout.floorplan.lef_units_per_micron
    with LefWriter(lef, db_units_per_micron) as lw:
        lw.write_file_header()
        lw.write_macro_header(macro_name, die_size_x, die_size_y)
        ports = {}
        for rect, layer, label, _ in layout.floorplan.resolve_lef_ports():
            ports.setdefault(label, []).append((layer, rect))
        signal_ports = {sp.name: sp.direction for sp in layout.netlist.ports}
        power_nets = set(layout.floorplan.power_nets)
        ground_nets = set(layout.floorplan.ground_nets)
        for pin, layer_rect_pairs in ports.items():
            if pin in power_nets:
                direction = "inout"
                use = "power"
                assert pin not in signal_ports
                assert pin not in ground_nets
            elif pin in ground_nets:
                direction = "inout"
                use = "ground"
                assert pin not in signal_ports
            else:
                direction = signal_ports[pin]
                use = "signal"
            lw.write_pin_header(pin, direction, use)
            for layer, rect in layer_rect_pairs:
                lw.write_port_header()
                lw.write_layer_entry(layer)
                lw.write_rect_entry(rect.x1, rect.y1, rect.x2, rect.y2)
                lw.write_port_footer()
            lw.write_pin_footer(pin)
        obs = {}
        rect_sources = [
            layout.floorplan.lef_obstructions,
            ((layer, rect) for rect, layer, _, _ in layout.floorplan.resolve_rects()),
        ]
        if layout.rects is not None:
            rect_sources.append(((layer, rect) for _, layer, rect in layout.rects))
        bbox_layers = set(layout.floorplan.lef_bbox_obstructions)
        sep_layers = set(layout.floorplan.lef_separate_obstructions)
        for layer_rect_pairs in rect_sources:
            for layer, rect in layer_rect_pairs:
                if layer in sep_layers:
                    obs.setdefault(layer, []).append(rect)
                elif layer in bbox_layers:
                    if layer not in obs:
                        obs[layer] = [rect.copy()]
                    obs_rect = obs[layer][0]
                    if rect.x1 < obs_rect.x1:
                        obs_rect.x1 = rect.x1
                    if rect.y1 < obs_rect.y1:
                        obs_rect.y1 = rect.y1
                    if rect.x2 > obs_rect.x2:
                        obs_rect.x2 = rect.x2
                    if rect.y2 > obs_rect.y2:
                        obs_rect.y2 = rect.y2
        lw.write_obs_header()
        for layer, rects in obs.items():
            lw.write_layer_entry(layer)
            for rect in rects:
                lw.write_rect_entry(rect.x1, rect.y1, rect.x2, rect.y2)
        lw.write_obs_footer()
        lw.write_macro_footer(macro_name)
        lw.write_file_footer()
