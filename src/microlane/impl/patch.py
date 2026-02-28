from math import ceil, sqrt

from ..util.structures import QuadTree, Rect, UnionFind


def add_patch_metals(layout):
    # classify rectangles by net and layer
    rect_groups = {}
    for net, layer, rect in layout.rects:
        rect_groups.setdefault((net, layer), []).append(rect)

    # add bridges between nearby rectangles of the same net
    updates = {}
    grid = layout.routing_grid
    for i in range(2):
        # run twice in case horizontal bridge causes vertical violation or vice versa
        for (net, layer), rects in rect_groups.items():
            if layer not in grid.layers:
                continue
            min_spacing = layout.rules.min_spacing[layer]
            qt = QuadTree()
            for rect in rects:
                qt.add_rect(rect)
            new_rects = []
            for rect in rects:
                rect_bloated = rect.bloated(min_spacing)
                nearby = list(qt.query_intersecting_rects(rect_bloated))
                for other in nearby:
                    if rect.touches_rect(other):
                        continue
                    other_bloated = other.bloated(min_spacing)
                    intersection = rect_bloated.intersection(other_bloated)
                    horizontal = intersection.y2 - intersection.y1 > 2 * min_spacing
                    vertical = intersection.x2 - intersection.x1 > 2 * min_spacing
                    if horizontal and not vertical:
                        bridge = Rect(
                            x1=intersection.x1,
                            y1=intersection.y1 + min_spacing,
                            x2=intersection.x2,
                            y2=intersection.y2 - min_spacing,
                        )
                    elif vertical and not horizontal:
                        bridge = Rect(
                            x1=intersection.x1 + min_spacing,
                            y1=intersection.y1,
                            x2=intersection.x2 - min_spacing,
                            y2=intersection.y2,
                        )
                    if any(dominator.contains_rect(bridge) for dominator in nearby):
                        continue
                    new_rects.append(bridge)
            updates[(net, layer)] = rects + new_rects
        rect_groups |= updates

    # group rectangles by connected components within layer
    rect_connected_groups = {}
    for (net, layer), rects in rect_groups.items():
        if layer not in grid.layers:
            # we aren't adding patch metals for vias, so it's easier to just keep them as a single group
            rect_connected_groups[(net, layer, 0)] = rects
            continue
        min_spacing = layout.rules.min_spacing[layer]
        qt = QuadTree()
        uf = UnionFind()
        for rect in rects:
            qt.add_rect(rect)
            uf.add(rect.as_tuple())
        for rect in rects:
            rect_bloated = rect.bloated(min_spacing)
            nearby = list(qt.query_intersecting_rects(rect_bloated))
            for other in nearby:
                if rect.touches_rect(other):
                    uf.union(rect.as_tuple(), other.as_tuple())
        for group, rect_set in enumerate(uf.sets()):
            rect_connected_groups[(net, layer, group)] = [
                Rect.from_tuple(r) for r in rect_set
            ]

    # grow nets under the minimum area threshold
    updates = {}
    for (net, layer, group), rects in rect_connected_groups.items():
        if layer not in grid.layers:
            continue
        grid_unit = layout.rules.grid_unit[layer]
        min_area = layout.rules.min_area[layer]
        x_coords = sorted({rect.x1 for rect in rects} | {rect.x2 for rect in rects})
        y_coords = sorted({rect.y1 for rect in rects} | {rect.y2 for rect in rects})
        area = 0
        for j in range(len(y_coords) - 1):
            y, y_next = y_coords[j], y_coords[j + 1]
            rects_filtered = [rect for rect in rects if rect.y1 <= y < rect.y2]
            for i in range(len(x_coords) - 1):
                x, x_next = x_coords[i], x_coords[i + 1]
                if (
                    next(
                        (rect for rect in rects_filtered if rect.x1 <= x < rect.x2),
                        None,
                    )
                    is not None
                ):
                    area += (x_next - x) * (y_next - y)
        if area >= min_area:
            continue
        area_diff = min_area - area
        resized_rects = []
        for rect in rects:
            # bloat the rectangle just enough to increase its area by area_diff
            x1, y1, x2, y2 = rect.x1, rect.y1, rect.x2, rect.y2
            half_perimeter = (x2 - x1) + (y2 - y1)
            # solve the quadratic equation
            increase = (sqrt(half_perimeter**2 + 4 * area_diff) - half_perimeter) / 4
            increase = ceil(increase / grid_unit) * grid_unit
            resized_rects.append(rect.bloated(increase))
        updates[(net, layer, group)] = resized_rects
    rect_connected_groups |= updates

    # rebuild layout.rects from rect_connected_groups
    layout.rects = [
        (net, layer, rect)
        for (net, layer, group), rects in rect_connected_groups.items()
        for rect in rects
    ]
