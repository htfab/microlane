from ..util.nodes import GateNode, NodeProcessor


class TechMapper(NodeProcessor):
    """synthesis step converting generic gates to technology specific standard cells"""

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        self.std_cell_library = self.config["std_cell_library"]
        self.tech_map = self.config["tech"]["tech_map"]
        return self.pass_through(node)

    def process_module(self, node):
        # props: name, ports, symbols, nets, net_counter, inst_counter, gates, continuous_assignments, body
        return self.pass_through(node)

    def process_port(self, node):
        # props: name, direction
        return self.pass_through(node)

    def process_symbol(self, node):
        # props: name, signed, data_type, range
        return self.pass_through(node)

    def process_net(self, node):
        # props: name
        return self.pass_through(node)

    def process_bit(self, node):
        # props: value
        return self.pass_through(node)

    def process_gate(self, node):
        # props: name, instance, terminals
        if node.name not in self.tech_map:
            raise RuntimeError(
                f"No tech map found for gate {node.name} into standard cell library {self.std_cell_library}"
            )
        name, terminal_map = self.tech_map[node.name]
        instance = node.instance
        gate_terminals = set(node.terminals)
        map_terminals = set(terminal_map.keys())
        if gate_terminals - map_terminals != set():
            raise RuntimeError(
                f"Terminals {gate_terminals - map_terminals} of gate {node.name} missing in tech map for {self.std_cell_library}"
            )
        if map_terminals - gate_terminals != set():
            raise RuntimeError(
                f"Terminals {map_terminals - gate_terminals} of gate {node.node} missing in circuit but specified in tech map for {self.std_cell_library}"
            )
        assert gate_terminals == map_terminals
        terminals = {}
        for term in gate_terminals:
            terminals[terminal_map[term]] = node.terminals[term]
        return GateNode(name=name, instance=instance, terminals=terminals)
