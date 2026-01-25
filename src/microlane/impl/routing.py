from ..util import progress
from ..util.database import AirWire, Array, Wavefront
from ..util.structures import QuadTree, Rect


# helper function to find the closest values to a given input in a Python range object
def closest_in_range(value, range_):
    start, stop, step = range_.start, range_.stop, range_.step
    if step > 0:
        clamped = min(max(value, start), stop)
        v1 = start + ((clamped - start) // step) * step
        v2 = start - (-(clamped - start) // step) * step
        res = set()
        if start <= v1 < stop:
            res.add(v1)
        if start <= v2 < stop:
            res.add(v2)
        return tuple(sorted(res))
    else:
        clamped = max(min(value, start), stop)
        v1 = start + ((clamped - start) // step) * step
        v2 = start - (-(clamped - start) // step) * step
        res = set()
        if start >= v1 > stop:
            res.add(v1)
        if start >= v2 > stop:
            res.add(v2)
        return tuple(sorted(res))


def run_routing(layout):
    # build the graph representation of the routing grid

    # setup
    die_width, die_height = layout.floorplan.die_size
    grid = layout.routing_grid
    num_vertices = 0
    vertex_pos = []
    vertex_lookup = {}
    vertex_adj = []
    vertex_obs = []
    layer_columns = {}
    layer_rows = {}
    layers = []
    vias = []
    for layer in grid.order:
        assert (layer in grid.layers) ^ (layer in grid.vias)
        if layer in grid.layers:
            layers.append(layer)
        else:
            vias.append(layer)

    cfg_dir_mult = layout.config["routing.wrong_direction_multiplier"]
    cfg_layer_mult = layout.config["routing.layer_multiplier"]
    cfg_via_penalty = layout.config["routing.via_penalty"]
    cfg_access_penalty = layout.config["routing.access_penalty"]
    cfg_pdn_space = layout.config["routing.pdn_extra_blockage"]
    cfg_cell_space = layout.config["routing.std_cell_extra_blockage"]

    progress.step("Grid construction", 1)
    progress.start_dots(2)

    # 2d grid for each metal (& local interconnect) layer
    for layer in layers:
        layer_grid = grid.layers[layer]
        columns = range(layer_grid.x.offset, die_width, layer_grid.x.raster)
        rows = range(layer_grid.y.offset, die_height, layer_grid.y.raster)
        layer_columns[layer] = columns
        layer_rows[layer] = rows
        horizontal_cost = layer_grid.x.raster * (
            1 if layer_grid.preferred == "horizontal" else cfg_dir_mult
        )
        vertical_cost = layer_grid.y.raster * (
            1 if layer_grid.preferred == "vertical" else cfg_dir_mult
        )
        if layer in cfg_layer_mult:
            multiplier = cfg_layer_mult[layer]
            horizontal_cost *= multiplier
            vertical_cost *= multiplier
        for y in rows:
            for x in columns:
                # create bidirectional mapping between vertex number and coordinates
                pos = (layer, x, y)
                vertex_pos.append(pos)
                vertex_adj.append([])
                vertex_obs.append([])
                vertex_lookup[pos] = num_vertices
                num_vertices += 1
        for y in rows:
            for x in columns:
                # for each vertex, store horizontally & vertically adjacent vertices
                pos = (layer, x, y)
                assert pos in vertex_lookup
                index = vertex_lookup[pos]
                pos_next_h = (layer, x + layer_grid.x.raster, y)
                if pos_next_h in vertex_lookup:
                    index_next_h = vertex_lookup[pos_next_h]
                    vertex_adj[index].append((horizontal_cost, index_next_h))
                    vertex_adj[index_next_h].append((horizontal_cost, index))
                pos_next_v = (layer, x, y + layer_grid.y.raster)
                if pos_next_v in vertex_lookup:
                    index_next_v = vertex_lookup[pos_next_v]
                    vertex_adj[index].append((vertical_cost, index_next_v))
                    vertex_adj[index_next_v].append((vertical_cost, index))
        progress.add_dot()

    # connections between adjacent layers through vias
    half_penalty = cfg_via_penalty // 2
    for via in vias:
        lower = grid.below[via]
        lower_grid = grid.layers[lower]
        lower_columns = layer_columns[lower]
        lower_rows = layer_rows[lower]
        upper = grid.above[via]
        upper_grid = grid.layers[upper]
        upper_columns = layer_columns[upper]
        upper_rows = layer_rows[upper]
        h_to_v = (
            lower_grid.preferred == "horizontal" and upper_grid.preferred == "vertical"
        )
        v_to_h = (
            lower_grid.preferred == "vertical" and upper_grid.preferred == "horizontal"
        )
        assert h_to_v ^ v_to_h
        if h_to_v:
            # lower layer horizontal, upper layer vertical
            columns = upper_columns
            rows = lower_rows
            adj_columns = {x: closest_in_range(x, lower_columns) for x in columns}
            adj_rows = {y: closest_in_range(y, upper_rows) for y in rows}
            for y in rows:
                for x in columns:
                    index = num_vertices
                    num_vertices += 1
                    pos = (via, x, y)
                    vertex_pos.append(pos)
                    vertex_adj.append([])
                    vertex_obs.append([])
                    vertex_lookup[pos] = index
                    # connections to lower layer
                    for ax in adj_columns[x]:
                        pos_lower = (lower, ax, y)
                        assert pos_lower in vertex_lookup
                        index_lower = vertex_lookup[pos_lower]
                        cost = abs(ax - x) + half_penalty
                        vertex_adj[index].append((cost, index_lower))
                        vertex_adj[index_lower].append((cost, index))
                        vertex_obs[index].append(index_lower)
                        vertex_obs[index_lower].append(index)
                    # connections to upper layer
                    for ay in adj_rows[y]:
                        pos_upper = (upper, x, ay)
                        assert pos_upper in vertex_lookup
                        index_upper = vertex_lookup[pos_upper]
                        cost = abs(ay - y) + half_penalty
                        vertex_adj[index].append((cost, index_upper))
                        vertex_adj[index_upper].append((cost, index))
                        vertex_obs[index].append(index_upper)
                        vertex_obs[index_upper].append(index)
        elif v_to_h:
            # lower layer vertical, upper layer horizontal
            columns = lower_columns
            rows = upper_rows
            adj_columns = {x: closest_in_range(x, upper_columns) for x in columns}
            adj_rows = {y: closest_in_range(y, lower_rows) for y in rows}
            for y in rows:
                for x in columns:
                    index = num_vertices
                    num_vertices += 1
                    pos = (via, x, y)
                    vertex_pos.append(pos)
                    vertex_adj.append([])
                    vertex_obs.append([])
                    vertex_lookup[pos] = index
                    # connections to lower layer
                    for ay in adj_rows[y]:
                        pos_lower = (lower, x, ay)
                        assert pos_lower in vertex_lookup
                        index_lower = vertex_lookup[pos_lower]
                        cost = abs(ay - y) + half_penalty
                        vertex_adj[index].append((cost, index_lower))
                        vertex_adj[index_lower].append((cost, index))
                        vertex_obs[index].append(index_lower)
                        vertex_obs[index_lower].append(index)
                    # connections to upper layer
                    for ax in adj_columns[x]:
                        pos_upper = (upper, ax, y)
                        assert pos_upper in vertex_lookup
                        index_upper = vertex_lookup[pos_upper]
                        cost = abs(ax - x) + half_penalty
                        vertex_adj[index].append((cost, index_upper))
                        vertex_adj[index_upper].append((cost, index))
                        vertex_obs[index].append(index_upper)
                        vertex_obs[index_upper].append(index)
        layer_columns[via] = columns
        layer_rows[via] = rows
        progress.add_dot()

    # vias going up and down near the same grid point are blocking each other
    for index in range(num_vertices):
        layer, _, _ = vertex_pos[index]
        if layer in layers:
            adj_vias = []
            for _, adj in vertex_adj[index]:
                adj_layer, _, _ = vertex_pos[adj]
                if adj_layer in vias:
                    adj_vias.append(adj)
            for v1 in adj_vias:
                for v2 in adj_vias:
                    if v1 != v2:
                        vertex_obs[v1].append(v2)

    progress.end_dots()
    progress.step("Term placement", 1)

    # find locations of terms in the netlist
    term_pos = {}
    for port in layout.ports:
        assert port.term not in term_pos
        term_pos[port.term] = [(port.layer, port.x, port.y)]
    for inst in layout.instances:
        pins = inst.resolve_pins(layout.cell_data)
        for pin, term in inst.terms.items():
            assert term not in term_pos
            term_pos[term] = pins[pin]

    # add terms to the grid graph
    term_access = {}
    vertex_to_pin_layer = {}
    for term, positions in term_pos.items():
        access = []
        for layer, x, y in positions:
            access_layer, _ = grid.pin_access[layer][0]
            pos = (access_layer, x, y)
            if pos in vertex_lookup:
                index = vertex_lookup[pos]
                access.append(index)
            else:
                index = num_vertices
                num_vertices += 1
                vertex_pos.append(pos)
                vertex_adj.append([])
                vertex_obs.append([])
                vertex_lookup[pos] = index
                access.append(index)
                for gx in closest_in_range(x, layer_columns[access_layer]):
                    for gy in closest_in_range(y, layer_rows[access_layer]):
                        pos_access = (access_layer, gx, gy)
                        assert pos_access in vertex_lookup
                        index_access = vertex_lookup[pos_access]
                        assert x == gx or y == gy
                        cost = abs(x - gx) + abs(y - gy)
                        vertex_adj[index].append((cost, index_access))
                        vertex_adj[index_access].append((cost, index))
                        vertex_obs[index].append(index_access)
                        vertex_obs[index_access].append(index)
            assert index not in vertex_to_pin_layer
            vertex_to_pin_layer[index] = layer
        term_access[term] = access

    progress.step("Access point setup", 1)

    # mark access points as blockages, to be removed when routing the net
    # also remove access points that belong to more than one term
    blocked = [False] * num_vertices
    ambiguous = set()
    for term, access in term_access.items():
        for index in access:
            if blocked[index]:
                ambiguous.add(index)
            blocked[index] = True
    for term in term_pos:
        nta = [index for index in term_access[term] if index not in ambiguous]
        assert len(nta) > 0
        term_access[term] = nta

    progress.step("Penalty setup", 1)

    # add a penalty near access points so they don't get blocked by other nets
    access_neighborhood = {}
    access_penalty_levels = len(cfg_access_penalty) - 1
    for net in layout.netlist.nets:
        an = set()
        for term in net.terms:
            for index in term_access[term]:
                an.add(index)
        access_neighborhood[net] = {0: an}
        for i in range(access_penalty_levels):
            an = set()
            for index in access_neighborhood[net][i]:
                for _, adj in vertex_adj[index]:
                    an.add(adj)
            access_neighborhood[net][i + 1] = an
    access_penalty_per_net = {}
    for net in layout.netlist.nets:
        for i in range(access_penalty_levels + 1):
            for index in access_neighborhood[net][i]:
                if i == 0 or index not in access_neighborhood[net][i - 1]:
                    access_penalty_per_net.setdefault(index, {})[net] = (
                        cfg_access_penalty[i]
                    )
    access_penalty = {}
    for index, penalties in access_penalty_per_net.items():
        access_penalty[index] = sum(penalties.values())

    progress.step("Blockage setup", 1)

    # generate blockages for the PDN & standard cells
    qt = {}
    blockage_rects = {}
    blockage_rects_upper = {}
    blockage_rects_lower = {}
    for layer in grid.order:
        qt[layer] = QuadTree()
        columns = layer_columns[layer]
        rows = layer_rows[layer]
        if layer in layers:
            layer_grid = grid.layers[layer]
            ww = layer_grid.x.width
            wh = layer_grid.y.width
            sp = layout.rules.min_spacing[layer]
            blockage_rects[layer] = Rect(
                x1=0, y1=0, x2=ww + 2 * sp, y2=wh + 2 * sp
            ).center_offset()
        elif layer in vias:
            uw, uh = grid.vias[layer].upper.size()
            blockage_rects_upper[layer] = Rect(
                x1=0, y1=0, x2=uw + 2 * sp, y2=uh + 2 * sp
            ).center_offset()
            lw, lh = grid.vias[layer].lower.size()
            blockage_rects_lower[layer] = Rect(
                x1=0, y1=0, x2=lw + 2 * sp, y2=lh + 2 * sp
            ).center_offset()
    for rect, layer, label, _ in layout.floorplan.resolve_rects():
        if layer in qt:
            if cfg_pdn_space:
                rect = rect.bloated(cfg_pdn_space)
            qt[layer].add_rect(rect)
    for inst in layout.instances:
        for layer, rect in inst.resolve_blockages(layout.cell_data):
            if cfg_cell_space:
                rect = rect.bloated(cfg_cell_space)
            qt[layer].add_rect(rect)
    feedback_unit = len(vertex_pos) // 32
    feedback_counter = 0
    progress.start_dots(2)
    for index, (layer, x, y) in enumerate(vertex_pos):
        if feedback_counter <= 0:
            feedback_counter = feedback_unit
            progress.add_dot()
        else:
            feedback_counter -= 1
        if layer in layers:
            pos_blockers = qt[layer].query_intersecting_rects(
                blockage_rects[layer].shifted(x, y)
            )
            if next(iter(pos_blockers), None) is not None:
                blocked[index] = True
        elif layer in vias:
            upper = grid.above[layer]
            pos_blockers = qt[upper].query_intersecting_rects(
                blockage_rects_upper[layer].shifted(x, y)
            )
            if next(iter(pos_blockers), None) is not None:
                blocked[index] = True
            lower = grid.below[layer]
            pos_blockers = qt[lower].query_intersecting_rects(
                blockage_rects_lower[layer].shifted(x, y)
            )
            if next(iter(pos_blockers), None) is not None:
                blocked[index] = True
    progress.end_dots()

    # maze router

    progress.step("Maze router", 1)
    verbose = layout.config["debug.verbose_routing"]
    if not verbose:
        progress.start_dots(2)

    # outer loop: iterate through all nets
    paths = []
    terms_used = []
    for net in layout.netlist.nets:
        targets = {}
        for term in net.terms:
            for index in term_access[term]:
                blocked[index] = False
                if term != net.driver:
                    targets[index] = term
        # middle loop: each time a new target is reached in a multi-point net
        net_paths = []
        while targets:
            found = None
            visited = set()
            predecessor = {}
            wf = Wavefront()
            if not net_paths:
                # first iteration, start from the net driver
                for index in term_access[net.driver]:
                    if index not in visited:
                        wf.push(0, index)
                        visited.add(index)
            else:
                # second or later iteration, start from points on the previous paths
                for path in net_paths:
                    for index in path:
                        if index not in visited:
                            wf.push(0, index)
                            visited.add(index)
            # inner loop: each point explored in Dijkstra's algorithm
            for cost, index in wf.iter_pop():
                for cost_inc, adj in vertex_adj[index]:
                    if not blocked[adj]:
                        if adj not in visited:
                            predecessor[adj] = index
                            if adj in targets:
                                found = adj
                                break
                            cost_inc += access_penalty.get(index, 0)
                            cost_inc -= access_penalty_per_net.get(index, {}).get(
                                net, 0
                            )
                            wf.push(cost + cost_inc, adj)
                            visited.add(adj)
                if found:
                    break
            if found is None:
                raise RuntimeError(f"Failed to route net {net.name}")
            # backtrace and save the path
            assert found in targets
            found_term = targets[found]
            terms_used.append((net.name, found_term, found))
            backtrace = []
            while found is not None:
                backtrace.append(found)
                found = predecessor.get(found)
            if not net_paths:
                terms_used.append((net.name, net.driver, backtrace[-1]))
            net_paths.append(backtrace)
            for index in term_access[found_term]:
                if index in targets:
                    del targets[index]
        # block off the path found
        for term in net.terms:
            for index in term_access[term]:
                blocked[index] = True
        for path in net_paths:
            for index in path:
                blocked[index] = True
                # vias obstruct all their neighbours on the adjacent layers
                for obs in vertex_obs[index]:
                    blocked[obs] = True
        paths.append((net, net_paths))
        if verbose:
            progress.log(f"Routed net {net.name}", 2)
        else:
            progress.add_dot()

    if not verbose:
        progress.end_dots()
    progress.step("Path drawing", 1)

    # draw rectangles corresponding to the paths found
    routing_rects = []
    base_rects = {}
    for layer in layers:
        layer_grid = grid.layers[layer]
        base_rects[layer] = Rect(
            x1=0, y1=0, x2=layer_grid.x.width, y2=layer_grid.y.width
        ).center_offset()
    for net, net_paths in paths:
        for path in net_paths:
            tail = []
            points = []
            for index in path:
                tail.append(vertex_pos[index])
                if len(tail) >= 3:
                    assert len(tail) == 3
                    layer0, x0, y0 = tail[0]
                    layer1, x1, y1 = tail[1]
                    layer2, x2, y2 = tail[2]
                    if layer0 == layer1 == layer2 and (
                        x0 == x1 == x2 or y0 == y1 == y2
                    ):
                        del tail[1]
                    else:
                        points.append(tail.pop(0))
            points.extend(tail)
            last_layer, last_x, last_y = None, None, None
            for layer, x, y in points:
                if last_layer is not None:
                    assert (
                        sum((layer == last_layer, last_layer in vias, layer in vias))
                        == 1
                    )
                    min_x, max_x = sorted((last_x, x))
                    min_y, max_y = sorted((last_y, y))
                    if layer == last_layer:
                        base = base_rects[layer]
                        rect = Rect(
                            x1=base.x1 + min_x,
                            y1=base.y1 + min_y,
                            x2=base.x2 + max_x,
                            y2=base.y2 + max_y,
                        )
                        routing_rects.append((net.name, layer, rect))
                    else:
                        if last_layer in vias:
                            l_layer, v_layer, v_x, v_y = (
                                layer,
                                last_layer,
                                last_x,
                                last_y,
                            )
                        else:
                            l_layer, v_layer, v_x, v_y = (
                                last_layer,
                                layer,
                                x,
                                y,
                            )
                        base = base_rects[l_layer]
                        rect = Rect(
                            x1=base.x1 + min_x,
                            y1=base.y1 + min_y,
                            x2=base.x2 + max_x,
                            y2=base.y2 + max_y,
                        )
                        routing_rects.append((net.name, l_layer, rect))
                        if layer in vias:
                            via_rects = grid.vias[v_layer]
                            routing_rects.append(
                                (
                                    net.name,
                                    grid.below[v_layer],
                                    via_rects.lower.shifted(v_x, v_y),
                                )
                            )
                            routing_rects.append(
                                (net.name, v_layer, via_rects.via.shifted(v_x, v_y))
                            )
                            routing_rects.append(
                                (
                                    net.name,
                                    grid.above[v_layer],
                                    via_rects.upper.shifted(v_x, v_y),
                                )
                            )
                last_layer, last_x, last_y = layer, x, y
    # draw pin access rectangles
    for net_name, term, index in terms_used:
        layer, x, y = vertex_pos[index]
        assert index in vertex_to_pin_layer
        pin_layer = vertex_to_pin_layer[index]
        for rect_layer, rect in grid.pin_access[pin_layer]:
            routing_rects.append((net_name, rect_layer, rect.shifted(x, y)))

    layout.rects = routing_rects

    # calculate wire length
    wire_length = 0
    for _, _, rect in layout.rects:
        wire_length += abs(rect.x2 - rect.x1 - rect.y2 + rect.y1)  # abs(w - h)
    layout.metrics["wire_length"] = wire_length

    # draw blockages for debugging
    blockages_in_gds = layout.config["debug.blockages_in_gds"]
    if blockages_in_gds:
        for layer, rects in blockage_rects.items():
            if layer in layers:
                for rect in qt[layer].query_all_rects():
                    layout.floorplan.rects.append(
                        Array(
                            layer=f"{layer}_blockage",
                            base_item=rect,
                            axis_refs=[],
                            label=None,
                        )
                    )

    # draw air wires for debugging
    air_wires_in_gds = layout.config["debug.air_wires_in_gds"]
    if air_wires_in_gds:
        layout.air_wires = []
        for net in layout.netlist.nets:
            source = net.driver
            _, sx, sy = term_pos[source][0]
            for target in net.terms:
                if target != source:
                    _, tx, ty = term_pos[target][0]
                    layout.air_wires.append(
                        AirWire(layer="met5", edge=((sx, sy), (tx, ty)), width=10)
                    )
