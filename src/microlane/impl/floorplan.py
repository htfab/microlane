from ..util.database import (
    Array,
    Axis,
    DesignRules,
    Floorplan,
    GridLines1D,
    GridLines2D,
    Instance,
    Layout,
    Net,
    Netlist,
    Port,
    RoutingGrid,
    StdCell,
    ViaRects,
)
from ..util.structures import Point, Rect


def load_floorplan_data(config):
    template = config["template"]
    data = config["tech"]["floorplans"][template]
    axes = {
        name: Axis(count=count, dx=dx, dy=dy)
        for name, (count, (dx, dy)) in data["axes"].items()
    }
    lists = data["lists"]
    rects = []
    for layer, ((x1, y1), (x2, y2)), axis_refs, label in data["rects"]:
        rects.append(
            Array(
                layer=layer,
                base_item=Rect(x1=x1, y1=y1, x2=x2, y2=y2),
                axis_refs=axis_refs,
                label=label,
            )
        )
    texts = []
    for layer, (x, y), axis_refs, label, label_size in data["texts"]:
        texts.append(
            Array(
                layer=layer,
                base_item=Point(x=x, y=y),
                axis_refs=axis_refs,
                label=label,
                data=label_size,
            )
        )
    ports = []
    for layer, (x, y), axis_refs, label in data["ports"]:
        ports.append(
            Array(
                layer=layer,
                base_item=Point(x=x, y=y),
                axis_refs=axis_refs,
                label=label,
            )
        )
    lef_ports = []
    for layer, ((x1, y1), (x2, y2)), axis_refs, label in data["lef_ports"]:
        lef_ports.append(
            Array(
                layer=layer,
                base_item=Rect(x1=x1, y1=y1, x2=x2, y2=y2),
                axis_refs=axis_refs,
                label=label,
            )
        )
    lef_obstructions = []
    for layer, ((x1, y1), (x2, y2)) in data["lef_obstructions"]:
        lef_obstructions.append((layer, Rect(x1=x1, y1=y1, x2=x2, y2=y2)))
    data = dict(data)
    data.update(
        {
            "axes": axes,
            "lists": lists,
            "rects": rects,
            "texts": texts,
            "ports": ports,
            "lef_ports": lef_ports,
            "lef_obstructions": lef_obstructions,
        }
    )
    floorplan = Floorplan(**data)
    return floorplan


def load_rules(config):
    data = config["tech"]["rules"]
    rules = DesignRules(
        grid_unit=data["grid_unit"],
        min_spacing=data["min_spacing"],
        min_area=data["min_area"],
    )
    return rules


def load_routing_grid(config):
    data = config["tech"]["routing_grid"]
    layers = {}
    for layer, rg in data["layers"].items():
        (xr, xo, xw), (yr, yo, yw), pref = rg
        layers[layer] = GridLines2D(
            x=GridLines1D(raster=xr, offset=xo, width=xw),
            y=GridLines1D(raster=yr, offset=yo, width=yw),
            preferred=pref,
        )
    vias = {}
    for via, rects in data["vias"].items():
        (lw, lh), (vw, vh), (uw, uh) = rects
        vias[via] = ViaRects(
            lower=Rect(x1=0, y1=0, x2=lw, y2=lh).center_offset(),
            via=Rect(x1=0, y1=0, x2=vw, y2=vh).center_offset(),
            upper=Rect(x1=0, y1=0, x2=uw, y2=uh).center_offset(),
        )
    pin_access = {}
    for pin_layer, access_rects in data["pin_access"].items():
        rects = []
        for layer, w, h in access_rects:
            rects.append((layer, Rect(x1=0, y1=0, x2=w, y2=h).center_offset()))
        pin_access[pin_layer] = rects
    order = data["order"]
    above = {layer: None for layer in layers}
    below = {layer: None for layer in layers}
    for i in range(0, len(order) - 2, 2):
        lower = order[i]
        via = order[i + 1]
        upper = order[i + 2]
        assert lower in layers
        assert via in vias
        assert upper in layers
        above[lower] = via
        below[via] = lower
        above[via] = upper
        below[upper] = via
    grid = RoutingGrid(
        layers=layers,
        vias=vias,
        pin_access=pin_access,
        order=order,
        above=above,
        below=below,
    )
    return grid


def load_cell_data(config):
    data = config["tech"]["std_cells"]
    cells = {}
    for name, cell in data.items():
        cells[name] = StdCell(
            roles=cell["roles"],
            sites=cell["sites"],
            boundary=Rect.from_tuple(cell["boundary"]),
            pins=cell["pins"],
            blockages=cell["blockages"],
        )
    return cells


def init_floorplan(netlist_node):
    config = netlist_node.config
    netlist = Netlist(
        ports=[
            Port(name=p.name, direction=p.direction, term=p.term)
            for p in netlist_node.ports
        ],
        instances=[
            Instance(name=i.instance, cell=i.name, terms=i.terms)
            for i in netlist_node.instances
        ],
        nets=[
            Net(name=n.name, terms=n.terms, driver=n.driver) for n in netlist_node.nets
        ],
        name=netlist_node.name,
    )
    return Layout(
        netlist=netlist,
        floorplan=load_floorplan_data(config),
        rules=load_rules(config),
        routing_grid=load_routing_grid(config),
        cell_data=load_cell_data(config),
        name=netlist.name,
        config=config,
        metrics={},
    )
