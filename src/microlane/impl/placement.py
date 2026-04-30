import random
from math import exp

from ..util import progress
from ..util.database import AirWire, Instance, Placement


def run_placement(layout):
    cox, coy = layout.floorplan.core_origin
    sw, sh = layout.floorplan.site_size
    gw, gh = layout.floorplan.site_grid
    esx = layout.config["placement.extra_space_x"]
    esy = layout.config["placement.extra_space_y"]

    progress.step("Setup", 1)

    # add ports as fixed rectangles from the floorplan
    nl_ports = {port.name: port for port in layout.netlist.ports}
    ports = []
    ports_seen = set()
    term_to_port = {}
    port_pos = []
    for i, (point, layer, label, access_type) in enumerate(
        layout.floorplan.resolve_ports()
    ):
        if label not in nl_ports:
            raise RuntimeError(f"Port {label} exists in floorplan but not in netlist")
        port = nl_ports[label].copy()
        port.x, port.y = point.as_tuple()
        port.layer = layer
        port.access_type = access_type
        ports.append(port)
        ports_seen.add(label)
        assert port.term not in term_to_port
        term_to_port[port.term] = i
        port_pos.append((port.x, port.y))
    layout.ports = ports
    num_ports = len(ports)
    for label in nl_ports:
        if label not in ports_seen:
            raise RuntimeError(f"Port {label} exists in netlist but not in floorplan")

    # initialize all cells at the bottom left corner
    sites = [[0 for i in range(gw)] for j in range(gh)]
    inst_pos = []
    inst_size = []
    term_to_inst = {}
    w_max = 0
    nl_instances = layout.netlist.instances
    num_instances = len(nl_instances)
    instances = []
    for i, inst in enumerate(nl_instances):
        inst = inst.copy()
        instances.append(inst)
        cell = layout.cell_data[inst.cell]
        inst_pos.append((0, 0))
        w, h = cell.sites
        assert h == 1
        w += esx
        inst_size.append(w)
        sites[0][w - 1] += 1
        if w > w_max:
            w_max = w
        for term in inst.terms.values():
            assert term not in term_to_inst
            term_to_inst[term] = i
    layout.instances = instances
    logic_instances = list(instances)
    for i in reversed(range(w_max)):
        sites[0][i] += sites[0][i + 1]

    # helper function for generating the placement structure corresponding to given gx & gy
    def get_placement(gx, gy, flip=False):
        return Placement(
            status="PLACED",
            x=cox + sw * gx,
            y=coy + sh * gy,
            orient=("S" if flip else "FS") if gy % 2 == 1 else ("FN" if flip else "N"),
        )

    # helper function to add endcap, tap and fill cells
    def add_special_cell(name, cell, gx, gy, width, flip):
        layout.instances.append(
            Instance(
                name=name, cell=cell, terms={}, placement=get_placement(gx, gy, flip)
            )
        )
        for s in range(width):
            sites[gy][gx + s] += 1

    # add endcap cells
    use_endcap_cells = layout.config["placement.use_endcap_cells"]
    if use_endcap_cells:
        endcaps = [
            name for name, data in layout.cell_data.items() if "endcap" in data.roles
        ]
        if len(endcaps) != 1:
            raise RuntimeError(
                f"Expected exactly one cell type marked as endcap, found: {endcaps}"
            )
        endcap = endcaps[0]
        endcap_width, endcap_height = layout.cell_data[endcap].sites
        assert endcap_height == 1
        for j in range(gh):
            add_special_cell(f"endcap_{j}_left", endcap, 0, j, endcap_width, flip=False)
            add_special_cell(
                f"endcap_{j}_left",
                endcap,
                gw - endcap_width,
                j,
                endcap_width,
                flip=True,
            )
    else:
        endcap_width = 0

    # add tap cells
    use_tap_cells = layout.config["placement.use_tap_cells"]
    if use_tap_cells:
        taps = [name for name, data in layout.cell_data.items() if "tap" in data.roles]
        if len(taps) != 1:
            raise RuntimeError(
                f"Expected exactly one cell type marked as tap, found: {taps}"
            )
        tap = taps[0]
        tap_width, tap_height = layout.cell_data[tap].sites
        tap_distance = layout.floorplan.tap_distance_sites
        assert tap_height == 1
        for j in range(gh):
            for i in range(gw // tap_distance - 1):
                if (i + j) % 2 == 0 or j in (0, gh - 1):
                    add_special_cell(
                        f"tap_{j}_{i}", tap, (i + 1) * tap_distance, j, tap_width, "N"
                    )

    # set up adjacency lists
    net_insts = []
    net_ports = []
    inst_nets = {}
    for i, net in enumerate(layout.netlist.nets):
        insts = set()
        ports = set()
        for j in net.terms:
            assert (j in term_to_port) ^ (j in term_to_inst)
            if j in term_to_port:
                ports.add(term_to_port[j])
            else:
                insts.add(term_to_inst[j])
        insts = sorted(insts)
        ports = sorted(ports)
        net_insts.append(insts)
        net_ports.append(ports)
        for j in insts:
            inst_nets.setdefault(j, []).append(i)
    inst_nets = [inst_nets[i] for i in range(num_instances)]

    # helper function for simulated annealing:
    # difference in half-perimeter wire length for an update being evaluated
    def hpwl_delta(update):
        delta = 0
        nets = set()
        for i in update:
            nets.update(inst_nets[i])
        for net in nets:
            first = True
            for i in net_insts[net]:
                pre_gx, pre_gy = inst_pos[i]
                pre_x = cox + sw * (pre_gx + inst_size[i] / 2)
                pre_y = coy + sh * (pre_gy + 1 / 2)
                if i in update:
                    post_gx, post_gy = update.get(i, (pre_gx, pre_gy))
                    post_x = cox + sw * (post_gx + inst_size[i] / 2)
                    post_y = coy + sh * (post_gy + 1 / 2)
                else:
                    post_x, post_y = pre_x, pre_y
                if first:
                    pre_x_min, pre_y_min = pre_x, pre_y
                    pre_x_max, pre_y_max = pre_x, pre_y
                    post_x_min, post_y_min = post_x, post_y
                    post_x_max, post_y_max = post_x, post_y
                    first = False
                else:
                    if pre_x < pre_x_min:
                        pre_x_min = pre_x
                    if pre_x > pre_x_max:
                        pre_x_max = pre_x
                    if pre_y < pre_y_min:
                        pre_y_min = pre_y
                    if pre_y > pre_y_max:
                        pre_y_max = pre_y
                    if post_x < post_x_min:
                        post_x_min = post_x
                    if post_x > post_x_max:
                        post_x_max = post_x
                    if post_y < post_y_min:
                        post_y_min = post_y
                    if post_y > post_y_max:
                        post_y_max = post_y
            assert not first
            for p in net_ports[net]:
                px, py = port_pos[p]
                if px < pre_x_min:
                    pre_x_min = px
                if px > pre_x_max:
                    pre_x_max = px
                if py < pre_y_min:
                    pre_y_min = px
                if py > pre_y_max:
                    pre_y_max = px
                if px < post_x_min:
                    post_x_min = px
                if px > post_x_max:
                    post_x_max = px
                if py < post_y_min:
                    post_y_min = px
                if py > post_y_max:
                    post_y_max = px
            pre_hpwl = (pre_x_max - pre_x_min) + (pre_y_max - pre_y_min)
            post_hpwl = (post_x_max - post_x_min) + (post_y_max - post_y_min)
            delta += post_hpwl - pre_hpwl
        return delta

    # simulated annealing setup
    random_seed = layout.config["placement.random_seed"]
    init_temperature = layout.config["placement.init_temperature"]
    cooling_factor = layout.config["placement.cooling_factor"]
    updates_per_gate = layout.config["placement.updates_per_gate"]

    random.seed(random_seed)
    temperature = init_temperature
    num_updates = num_instances * updates_per_gate
    overlap_penalty = (sw * gw + sh * gh) * (num_instances + num_ports)
    gh_div = gh // (1 + esy)

    progress.step("Annealing", 1)
    progress.start_dots(2)

    # external loop (temperature cooling)
    while True:
        total_delta = 0
        # internal loop (instance moves & swaps)
        for u in range(num_updates):
            do_swap = random.randrange(6) == 0
            if do_swap:
                i = random.randrange(num_instances)
                j = random.randrange(num_instances)
                if i == j:
                    continue
                igx, igy = inst_pos[i]
                isz = inst_size[i]
                jgx, jgy = inst_pos[j]
                jsz = inst_size[j]
                if igx + jsz > gw or jgx + isz > gw:
                    continue  # doesn't fit after swap
                delta = hpwl_delta({i: (jgx, jgy), j: (igx, igy)})
                overlap_delta = 0
                if isz > jsz:
                    for s in range(jsz, isz):
                        overlap_delta -= sites[igy][igx + s] - 1
                        overlap_delta += sites[jgy][jgx + s]
                elif jsz > isz:
                    for s in range(isz, jsz):
                        overlap_delta -= sites[jgy][jgx + s] - 1
                        overlap_delta += sites[igy][igx + s]
                delta += overlap_delta * overlap_penalty
            else:
                i = random.randrange(num_instances)
                igx, igy = inst_pos[i]
                isz = inst_size[i]
                ngx = random.randrange(endcap_width + esx, gw - endcap_width - isz + 1)
                ngy = random.randrange(gh_div) * (1 + esy)
                delta = hpwl_delta({i: (ngx, ngy)})
                overlap_delta = 0
                for s in range(isz):
                    overlap_delta -= sites[igy][igx + s] - 1
                    overlap_delta += sites[ngy][ngx + s]
                delta += overlap_delta * overlap_penalty
            accept = delta < 0 or random.random() < exp(-delta / temperature)
            if accept:
                total_delta += delta
                if do_swap:
                    inst_pos[i] = (jgx, jgy)
                    inst_pos[j] = (igx, igy)
                    if isz > jsz:
                        for s in range(jsz, isz):
                            sites[igy][igx + s] -= 1
                            sites[jgy][jgx + s] += 1
                    elif jsz > isz:
                        for s in range(isz, jsz):
                            sites[jgy][jgx + s] -= 1
                            sites[igy][igx + s] += 1
                else:
                    inst_pos[i] = (ngx, ngy)
                    for s in range(isz):
                        sites[igy][igx + s] -= 1
                        sites[ngy][ngx + s] += 1
        if total_delta >= 0:
            break
        temperature *= cooling_factor
        progress.add_dot()
    progress.end_dots()

    progress.step("Postprocessing", 1)

    # undo dummy fill added for extra space
    for i in range(num_instances):
        gx, gy = inst_pos[i]
        osz = inst_size[i]
        nsz = osz - esx
        inst_size[i] = nsz
        for j in range(nsz, osz):
            sites[gy][gx + j] -= 1

    # set placement in layout.instances according to inst_pos
    for i, inst in enumerate(logic_instances):
        gx, gy = inst_pos[i]
        inst.placement = get_placement(gx, gy)

    # add fill cells
    fillers_by_size = {}
    fill_sites = 0
    for name, data in layout.cell_data.items():
        if "fill" in data.roles:
            w, h = data.sites
            assert h == 1
            if w in fillers_by_size:
                raise RuntimeError(
                    f"Ambiguous fill cell for size {w}: {fillers_by_size[w]}, {name}"
                )
            fillers_by_size[w] = name
    if 1 not in fillers_by_size:
        raise RuntimeError("No fill cell of size 1 found")
    max_filler_size = max(fillers_by_size)
    max_size_up_to = []
    current_size = 0
    for i in range(max_filler_size + 1):
        if i in fillers_by_size:
            current_size = i
        max_size_up_to.append(current_size)
    for j in range(gh):
        for i in range(gw):
            if sites[j][i] > 1:
                raise RuntimeError(f"Overlapping cells at ({i}, {j}) after placement")
            if sites[j][i] == 0:
                max_filler_size_capped = min(max_filler_size, gw - i)
                free_width = next(
                    (
                        k
                        for k in range(1, max_filler_size_capped)
                        if sites[j][i + k] > 0
                    ),
                    max_filler_size_capped,
                )
                filler_width = max_size_up_to[free_width]
                filler = fillers_by_size[filler_width]
                add_special_cell(
                    f"fill_{j}_{i}", filler, i, j, filler_width, flip=False
                )
                fill_sites += filler_width
    total_sites = gh * gw
    utilization = (total_sites - fill_sites) / total_sites
    layout.metrics["utilization"] = utilization

    # draw air wires for debugging
    air_wires_in_gds = layout.config["debug.air_wires_in_gds"]
    if air_wires_in_gds:
        layout.air_wires = []
        for i, inst in enumerate(logic_instances):
            ports = set()
            insts = set()
            for net in inst_nets[i]:
                ports.update(net_ports[net])
                insts.update(net_insts[net])
            icx = inst.placement.x + inst_size[i] * sw / 2
            icy = inst.placement.y + sh / 2
            for port in sorted(ports):
                pcx, pcy = port_pos[port]
                layout.air_wires.append(
                    AirWire(layer="met5", edge=((icx, icy), (pcx, pcy)), width=20)
                )
            for j in sorted(insts):
                if j > i:
                    other = logic_instances[j]
                    jcx = other.placement.x + inst_size[j] * sw / 2
                    jcy = other.placement.y + sh / 2
                    layout.air_wires.append(
                        AirWire(layer="met5", edge=((icx, icy), (jcx, jcy)), width=20)
                    )
