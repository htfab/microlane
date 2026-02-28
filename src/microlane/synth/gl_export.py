from ..util.nodes import GateNode, ModuleNode, NetlistNode, NetNode, PortNode, RootNode
from ..util.structures import UnionFind


class NameFixer:
    """converts wire & instance names to a format compatible with verilog output"""

    def __init__(self, ports):
        self.mapping = {}
        self.existing_names = set()
        self.ports = set(ports)

    def is_port(self, name):
        basename = name.split("[")[0]
        return basename in self.ports

    def resolve(self, name):
        if name in self.mapping:
            name = self.mapping[name]
            return name + (" " if name.startswith("\\") else "")
        elif self.is_port(name):
            self.mapping[name] = name
            assert name not in self.existing_names
            self.existing_names.add(name)
            return name
        original_name = name
        if name.startswith("$"):
            name = f"_{name[1:]}_"
        valid = True
        for c in name:
            if not (c.isalpha() or c.isdigit() or c in "$_"):
                valid = False
        if name[0].isdigit() or name[0] == "$":
            valid = False
        if name[0] == "\\":
            valid = True
        if not valid:
            name = f"\\{name}"
        if name in self.existing_names:
            base_name = name
            unique_suffix = 0
            while True:
                name = f"{base_name}${unique_suffix}"
                if name not in self.existing_names:
                    break
                unique_suffix += 1
        assert name not in self.existing_names
        self.mapping[original_name] = name
        return name + (" " if name.startswith("\\") else "")


def prepare_ports(module, config):
    pnl_terminals = config["tech"]["pnl_terminals"]
    pnl_nets = set(pnl_terminals.values())
    nl_ports = []
    pnl_ports = []
    port_dirs = {}
    for net in pnl_nets:
        pnl_ports.append(net)
        port_dirs[net] = "inout"
    for port in module.ports:
        assert isinstance(port, PortNode)
        nl_ports.append(port.name)
        pnl_ports.append(port.name)
        port_dirs[port.name] = port.direction
    return (pnl_terminals, pnl_nets, nl_ports, pnl_ports, port_dirs)


def write_gl_verilog(node, file, powered=False):
    assert isinstance(node, RootNode)
    for module in node.modules:
        assert isinstance(module, ModuleNode)
        pnl_terminals, pnl_nets, nl_ports, pnl_ports, port_dirs = prepare_ports(
            module, node.config
        )
        write_ports = pnl_ports if powered else nl_ports
        file.write(f"module {module.name} (")
        for i, port in enumerate(write_ports):
            if i != 0:
                file.write(",\n    ")
            file.write(f"{port}")
        file.write(");\n")
        for port in write_ports:
            if port in pnl_nets:
                port_range = None
            else:
                port_range = module.symbols[port].index
            if port_range is None:
                range_str = ""
            elif port_range.step == -1:
                range_max = port_range.start
                range_min = port_range.stop + 1
                range_str = f" [{range_max}:{range_min}]"
            elif port_range.step == 1:
                range_min = port_range.start
                range_max = port_range.stop - 1
                range_str = f" [{range_min}:{range_max}]"
            else:
                raise RuntimeError(f"Invalid range for port: {port}")
            file.write(f"{port_dirs[port]}{range_str} {port};\n")
        file.write("\n")
        name_fixer = NameFixer(set(pnl_ports))
        for net in module.nets:
            assert isinstance(net, NetNode)
            name = name_fixer.resolve(net.name)
            if not name_fixer.is_port(net.name):
                file.write(f"wire {name};\n")
        file.write("\n")
        for gate in module.gates:
            assert isinstance(gate, GateNode)
            instance = name_fixer.resolve(gate.instance)
            file.write(f"{gate.name} {instance} (")
            terms = []
            if powered:
                terms += list(pnl_terminals.items())
            for k, v in gate.terminals.items():
                assert isinstance(v, NetNode)
                vname = name_fixer.resolve(v.name)
                terms.append((k, vname))
            for i, (k, v) in enumerate(terms):
                if i != 0:
                    file.write(",\n    ")
                file.write(f".{k}({v})")
            file.write(");\n")
        file.write("\n")
        for k, v in sorted(module.continuous_assignments.items()):
            kname = name_fixer.resolve(k)
            vname = name_fixer.resolve(v.name)
            file.write(f"assign {kname} = {vname};\n")
        file.write("endmodule\n")


def get_netlist(node):
    assert isinstance(node, RootNode)
    assert len(node.modules) == 1
    std_cells = node.config["tech"]["std_cells"]
    module = node.modules[0]
    _, _, nl_ports, pnl_ports, port_dirs = prepare_ports(module, node.config)
    nets = {}
    drivers = {}
    nn_ports = []
    instances = []
    current_term = 0
    name_fixer = NameFixer(set(pnl_ports))
    for net in module.nets:
        name = name_fixer.resolve(net.name)
        nets[name] = []
        drivers[name] = []
    for port in nl_ports:
        assert port in module.symbols
        symbol = module.symbols[port]
        if symbol.index is None:
            port_nets = [port]
        else:
            port_nets = [f"{port}[{index}]" for index in symbol.index]
        for net in port_nets:
            assert net in nets
            nets[net].append(current_term)
            if port_dirs[port] == "input":
                drivers[net].append(current_term)
            nn_ports.append(
                PortNode(name=net, direction=port_dirs[port], term=current_term)
            )
            current_term += 1
    for gate in module.gates:
        assert isinstance(gate, GateNode)
        assert gate.name in std_cells
        instance = name_fixer.resolve(gate.instance)
        terms = {}
        std_cell_outputs = std_cells[gate.name]["outputs"]
        for k, v in gate.terminals.items():
            assert isinstance(v, NetNode)
            vname = name_fixer.resolve(v.name)
            assert vname in nets
            nets[vname].append(current_term)
            if k in std_cell_outputs:
                drivers[vname].append(current_term)
            terms[k] = current_term
            current_term += 1
        instances.append(GateNode(instance=instance, name=gate.name, terms=terms))
    uf_nets = UnionFind()
    for net in nets:
        uf_nets.add(net)
    for k, v in sorted(module.continuous_assignments.items()):
        kname = name_fixer.resolve(v.name)
        vname = name_fixer.resolve(v.name)
        assert kname in nets
        assert vname in nets
        uf_nets.union(kname, vname)
    joined_nets = {}
    for k, v in nets.items():
        joined_nets.setdefault(uf_nets.find(k), []).extend(v)
    joined_drivers = {}
    for k, v in drivers.items():
        joined_drivers.setdefault(uf_nets.find(k), []).extend(v)
    nets = []
    for net in sorted(joined_nets):
        assert net in joined_drivers
        assert len(joined_drivers[net]) == 1
        nets.append(
            NetNode(name=net, terms=joined_nets[net], driver=joined_drivers[net][0])
        )
    return NetlistNode(
        name=module.name,
        num_terms=current_term,
        nets=nets,
        ports=nn_ports,
        instances=instances,
        config=node.config,
    )
