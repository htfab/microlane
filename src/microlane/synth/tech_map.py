from ..util.nodes import ModuleNode, NodeProcessor


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
        assert node.body is None
        self.nets = node.nets
        self.gates = []
        self.net_counter = node.net_counter
        self.inst_counter = 0

        tech_map_inst = self.tech_map(self)
        for gate in node.gates:
            tech_map_inst.map_gate(gate.name, gate.terminals)

        nn = ModuleNode(
            name=node.name,
            ports=node.ports,
            symbols=node.symbols,
            nets=self.nets,
            gates=self.gates,
            continuous_assignments=node.continuous_assignments,
            net_counter=self.net_counter,
            inst_counter=self.inst_counter,
        )
        return nn
