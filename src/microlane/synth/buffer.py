from ..util.logic import GATE_INPUTS, GT
from ..util.nodes import ModuleNode, NetNode, NodeProcessor


class Bufferer(NodeProcessor):
    """synthesis step inserting buffers for nets exceeding the maximum fanout"""

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        return self.pass_through(node)

    def process_module(self, node):
        # props: name, ports, symbols, nets, net_counter, inst_counter, gates, continuous_assignments, body
        assert node.body is None
        self.nets = node.nets
        self.gates = node.gates
        self.net_counter = node.net_counter
        self.inst_counter = node.inst_counter

        # collect gates driven by each net
        # (for the time being we ignore output pins and net aliases stored as continuous_assignments
        #  - they are not needed for the common case of clock & global reset buffering)
        driven_gates = {}
        for gate in self.gates:
            for k, v in gate.terminals.items():
                if k in GATE_INPUTS:
                    assert isinstance(v, NetNode)
                    driven_gates.setdefault(v.name, []).append((gate, k))

        # process nets driving too many gates
        max_fanout = self.config["synth.max_fanout"]
        for net_name, net_fanout in driven_gates.items():
            while len(net_fanout) > max_fanout:
                # split driven gates into groups of <=max_fanout
                groups = []
                current_group = []
                for f in net_fanout:
                    if len(current_group) >= max_fanout:
                        groups.append(current_group)
                        current_group = []
                    current_group.append(f)
                groups.append(current_group)
                # process each group
                new_net_fanout = []
                for group in groups:
                    assert len(group) >= 1
                    if len(group) == 1:
                        new_net_fanout.append(group[0])
                        continue
                    # group size >=1, add a buffer
                    buf_net = self.create_gate(GT.BUF, "X", A=NetNode(name=net_name))
                    buf_gate = self.gates[-1]
                    # update gates in the group to use the buffered net
                    for gate, term in group:
                        gate.terminals[term] = buf_net
                    # save buffer in the new fanout list in case we need one more round of buffering
                    new_net_fanout.append((buf_gate, "A"))
                # prepare for next round
                net_fanout = new_net_fanout

        # Return the modified module
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
        del self.nets, self.gates, self.net_counter, self.inst_counter
        return nn
