import heapq
from math import cos, pi, sin

from .structures import DataClass, Rect


class Placement(DataClass):
    """placement data including status (UNPLACED, PLACED, FIXED, COVER), coordinates and orientation"""

    _attributes = ["status", "x", "y", "orient"]
    _defaults = {"status": "UNPLACED", "x": None, "y": None, "orient": None}
    _show_always = {"status"}


class Port(DataClass):
    """external pin of the entire design, as used in netlist or floorplan"""

    _attributes = ["name", "direction", "term", "layer", "x", "y"]
    _defaults = {"layer": None, "x": None, "y": None}


class Instance(DataClass):
    """standard cell instance"""

    _attributes = ["name", "cell", "terms", "placement"]
    _defaults = {"placement": None}

    def _resolve_point(self, boundary, x, y):
        orient = self.placement.orient
        assert orient in ("N", "FN", "S", "FS")
        if orient in ("N", "FS"):
            rx = self.placement.x + boundary.x1 + x
        else:
            rx = self.placement.x + boundary.x2 - x
        if orient in ("N", "FN"):
            ry = self.placement.y + boundary.y1 + y
        else:
            ry = self.placement.y + boundary.y2 - y
        return rx, ry

    def resolve_pins(self, cell_data):
        assert self.cell in cell_data
        assert self.placement is not None
        assert self.placement.status != "UNPLACED"
        cell = cell_data[self.cell]
        boundary = cell.boundary
        pins = {}
        for label, points in cell.pins.items():
            for layer, x, y in points:
                rx, ry = self._resolve_point(boundary, x, y)
                pins.setdefault(label, []).append((layer, rx, ry))
        return pins

    def resolve_blockages(self, cell_data):
        assert self.cell in cell_data
        assert self.placement is not None
        assert self.placement.status != "UNPLACED"
        cell = cell_data[self.cell]
        boundary = cell.boundary
        blockages = []
        for layer, x1, y1, x2, y2 in cell.blockages:
            rx1, ry1 = self._resolve_point(boundary, x1, y1)
            rx2, ry2 = self._resolve_point(boundary, x2, y2)
            blockages.append((layer, Rect(x1=rx1, y1=ry1, x2=rx2, y2=ry2)))
        return blockages


class Net(DataClass):
    """net connecting two or more terms"""

    _attributes = ["name", "terms", "driver"]


class Netlist(DataClass):
    """netlist received as input for placement"""

    _attributes = ["ports", "instances", "nets", "name"]
    _defaults = {"name": None}


class Axis(DataClass):
    """repetition vector & count for an array of objects"""

    _attributes = ["count", "dx", "dy"]


class Array(DataClass):
    """a base item repeated for a cartesian product of axes"""

    _attributes = ["layer", "base_item", "axis_refs", "label", "data"]
    _defaults = {"data": None}


class Floorplan(DataClass):
    """information about the layout that doesn't depend on the netlist"""

    _attributes = [
        "die_size",
        "core_origin",
        "site_size",
        "site_grid",
        "tap_distance_sites",
        "power_nets",
        "ground_nets",
        "axes",
        "lists",
        "rects",
        "texts",
        "ports",
        "lef_units_per_micron",
        "lef_ports",
        "lef_obstructions",
        "lef_bbox_obstructions",
        "lef_separate_obstructions",
    ]

    @staticmethod
    def _resolve_axis(items, axis):
        for item in items:
            for i in range(axis.count):
                yield item.shifted(i * axis.dx, i * axis.dy)

    def _resolve_array(self, array):
        items = [array.base_item]
        for axis_ref in array.axis_refs:
            axis = self.axes[axis_ref]
            items = self._resolve_axis(items, axis)
        label = array.label
        data = array.data
        if label in self.lists:
            for item, label in zip(items, self.lists[label]):
                yield (item, label, data)
        else:
            for item in items:
                yield (item, label, data)

    def _resolve_array_list(self, array_list):
        for array in array_list:
            for item, label, data in self._resolve_array(array):
                yield (item, array.layer, label, data)

    def resolve_rects(self):
        yield from self._resolve_array_list(self.rects)

    def resolve_texts(self):
        yield from self._resolve_array_list(self.texts)

    def resolve_ports(self):
        yield from self._resolve_array_list(self.ports)

    def resolve_lef_ports(self):
        yield from self._resolve_array_list(self.lef_ports)


class StdCell(DataClass):
    """information about a standard cell as read from the tech files"""

    _attributes = ["roles", "sites", "boundary", "pins", "blockages"]


class AirWire(DataClass):
    """a line connecting two points in the gds, used for debugging"""

    _attributes = ["layer", "edge", "width", "polygon_sides"]
    _defaults = {"polygon_sides": 16}

    def as_polygon(self):
        (x1, y1), (x2, y2) = self.edge
        n = self.polygon_sides
        polygon = []
        for i in range(n):
            phi = i / n * 2 * pi
            ux, uy = cos(phi), sin(phi)
            x, y = max((x1, y1), (x2, y2), key=lambda p: p[0] * ux + p[1] * uy)
            px, py = round(x + ux * self.width / 2), round(y + uy * self.width / 2)
            polygon.append((px, py))
        return self.layer, polygon


class GridLines1D(DataClass):
    """columns or rows of a single layer of the routing grid"""

    _attributes = ["raster", "offset", "width"]


class GridLines2D(DataClass):
    """a single layer of the routing grid"""

    _attributes = ["x", "y", "preferred"]


class ViaRects(DataClass):
    """rectangles to be drawn around a via on various layers to satisfy drc"""

    _attributes = ["lower", "via", "upper"]


class RoutingGrid(DataClass):
    """all layers and vias in the routing grid"""

    _attributes = ["layers", "vias", "pin_access", "order", "above", "below"]


class DesignRules(DataClass):
    """DRC rules from tech data"""

    _attributes = ["grid_unit", "min_spacing", "min_area"]


class Layout(DataClass):
    """root object for storing design related information during the implementation flow"""

    _attributes = [
        "name",
        "ports",
        "instances",
        "terms",
        "netlist",
        "cell_data",
        "rules",
        "floorplan",
        "routing_grid",
        "rects",
        "air_wires",
        "config",
        "metrics",
    ]

    _defaults = {
        "name": None,
        "ports": None,
        "instances": None,
        "terms": [],
        "netlist": None,
        "cell_data": None,
        "rules": None,
        "floorplan": None,
        "routing_grid": None,
        "rects": None,
        "air_wires": None,
    }


class Wavefront(DataClass):
    """heap data structure for pending grid points in the maze router"""

    _attributes = ["heap"]

    def __init__(self):
        self.heap = []

    def push(self, cost, index):
        heapq.heappush(self.heap, (cost, index))

    def iter_pop(self):
        while self.heap:
            yield heapq.heappop(self.heap)
