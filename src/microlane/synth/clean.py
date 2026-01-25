from ..util.logic import GATE_INPUTS, GATE_OUTPUTS, GT
from ..util.nodes import (
    BitNode,
    DontCareNode,
    GateNode,
    ModuleNode,
    NetNode,
    NodeProcessor,
)
from ..util.structures import UnionFind


class Cleaner(NodeProcessor):
    """cleans up unnecessary gates from the design

    - removes gates whose output is never used
    - merges gates with identical inputs
    - merges chains of buffers, inverters and continuous assignments
    - removes nets that became superfluous in the clean-up
    - replaces constant bits with $net_0 and $net_1 (tie cells added in bit_blast)
    """

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        return self.pass_through(node)

    def convert_to_net(self, node):
        """converts a bit or don't care to an equivalent net (connected to a pre-existing tie cell)"""
        if isinstance(node, NetNode):
            return node
        elif isinstance(node, BitNode):
            assert node.value in (0, 1)
            if node.value == 0:
                return NetNode(name="$net_0")
            elif node.value == 1:
                return NetNode(name="$net_1")
        elif isinstance(node, DontCareNode):
            return NetNode(name="$net_0")
        else:
            raise RuntimeError("Unexpected node type: {node}")

    def convert_bits_to_nets(self):
        """replaces every constant 0 or 1 (or don't care) in the design with a net connected to a tie cell"""
        for g in self.gates:
            updates = {}
            for k, v in g.terminals.items():
                if not isinstance(v, NetNode):
                    updates[k] = self.convert_to_net(v)
            if updates:
                g.terminals |= updates
        for k, v in self.continuous_assignments.items():
            if not isinstance(v, NetNode):
                self.continuous_assignments[k] = self.convert_to_net(v)

    def convert_assignments_to_buffers(self):
        """replaces continuous assignments with buffers so that we only need to deal with gates"""
        for k, v in self.continuous_assignments.items():
            self.create_gate(GT.BUF, A=v, X=NetNode(name=k))
        self.continuous_assignments = {}

    def build_lookup_tables(self):
        """creates dictionaries to find instances by adjacent nets and vice versa"""
        self.lu_inst_gate = {}
        self.lu_inst_inputs = {}
        self.lu_inst_outputs = {}
        self.lu_net_input = {}
        self.lu_net_outputs = {}
        for net in self.nets:
            self.lu_net_input[net.name] = None
            self.lu_net_outputs[net.name] = []
        for gate in self.gates:
            inst = gate.instance
            self.lu_inst_gate[inst] = gate
            self.lu_inst_inputs[inst] = []
            self.lu_inst_outputs[inst] = []
            for k, v in gate.terminals.items():
                assert k in GATE_INPUTS + GATE_OUTPUTS
                if k in GATE_INPUTS:
                    self.lu_inst_inputs[inst].append(v.name)
                    self.lu_net_outputs[v.name].append(inst)
                elif k in GATE_OUTPUTS:
                    self.lu_inst_outputs[inst].append(v.name)
                    assert self.lu_net_input[v.name] is None
                    self.lu_net_input[v.name] = inst

    def collect_io_nets(self):
        """generates sets of input and output nets based on the port list"""
        self.input_nets = set()
        self.output_nets = set()
        ports = {port.name: port.direction for port in self.ports}
        for net in self.nets:
            basename = net.name.split("[")[0]
            if net.name.startswith("\\"):
                basename = net.name
            if basename in ports:
                port_dir = ports[basename]
                if port_dir == "input":
                    self.input_nets.add(net.name)
                elif port_dir == "output":
                    self.output_nets.add(net.name)
                elif port_dir == "inout":
                    if self.lu_net_input[net.name] is not None:
                        self.output_nets.add(net.name)
                    else:
                        self.input_nets.add(net.name)
                else:
                    raise ValueError(f"Unexpected port direction: {port_dir}")

    def replace_partially_used_gate(self, gate, visited_nets):
        """creates a replacement for a two-output gate where only one output is used"""
        if gate.name == GT.HA:
            t = gate.terminals
            A, B, COUT, SUM = t["A"], t["B"], t["COUT"], t["SUM"]
            assert A.name in visited_nets
            assert B.name in visited_nets
            assert (COUT.name in visited_nets) + (SUM.name in visited_nets) == 1
            if COUT.name in visited_nets:
                # COUT output of HA gate is equivalent to an AND2 gate
                self.create_gate(GT.AND, A=A, B=B, X=COUT)
            elif SUM.name in visited_nets:
                # SUM output of HA gate is equivalent to a XOR2 gate
                self.create_gate(GT.XOR, A=A, B=B, X=SUM)
        elif gate.name == GT.FA:
            t = gate.terminals
            A, B, CIN, COUT, SUM = t["A"], t["B"], t["CIN"], t["COUT"], t["SUM"]
            assert A.name in visited_nets
            assert B.name in visited_nets
            assert CIN.name in visited_nets
            assert (COUT.name in visited_nets) + (SUM.name in visited_nets) == 1
            if COUT.name in visited_nets:
                # COUT output of FA gate is equivalent to a MAJ3 gate
                # (splitting into two AND2 and two OR2 gates for the time being)
                A_AND_B = self.create_gate(GT.AND, "X", A=A, B=B)
                A_OR_B = self.create_gate(GT.OR, "X", A=A, B=B)
                OIA_A_B_CIN = self.create_gate(GT.AND, "X", A=A_OR_B, B=CIN)
                self.create_gate(GT.OR, A=A_AND_B, B=OIA_A_B_CIN, X=COUT)
            elif SUM.name in visited_nets:
                # SUM output of FA gate is equivalent to a XOR3 gate
                # (splitting into two XOR gates for the time being)
                A_XOR_B = self.create_gate(GT.XOR, "X", A=A, B=B)
                self.create_gate(GT.XOR, A=A_XOR_B, B=CIN, X=SUM)
        else:
            raise RuntimeError(f"Unexpected partially used gate: {gate}")

    def cleanup_start(self):
        """clean-up steps to run before collecting sets of equivalent nets"""

        # resolve constant and don't care bits
        self.convert_bits_to_nets()

        # replace continuous assignments with buffers so that we only need to deal with gates
        self.convert_assignments_to_buffers()

        # build lookup tables for gates and nets
        self.build_lookup_tables()

        # build lists of input and output nets
        self.collect_io_nets()

        # walk the graph from the outputs to find which gates and nets are used
        stack = list(self.output_nets) + ["$net_0", "$net_1"]
        visited_nets = set(stack) | self.input_nets
        visited_instances = set()
        while stack:
            net = stack.pop()
            inst = self.lu_net_input[net]
            if inst is None:
                continue
            visited_instances.add(inst)
            for dep in self.lu_inst_inputs[inst]:
                if dep not in visited_nets:
                    visited_nets.add(dep)
                    stack.append(dep)

        # only keep gates and nets that were reached
        self.original_nets, self.nets = self.nets, []
        self.original_gates, self.gates = self.gates, []
        for net in self.original_nets:
            if net.name in visited_nets:
                self.nets.append(net)
        for gate in self.original_gates:
            inst = gate.instance
            if inst in visited_instances:
                if all(net in visited_nets for net in self.lu_inst_outputs[inst]):
                    self.gates.append(gate)
                else:
                    # only one output of a two-output gate is used
                    self.replace_partially_used_gate(gate, visited_nets)

        # rebuild the lookup tables to account for changed gates and nets
        self.build_lookup_tables()

        # keep track of gates to delete
        self.deleted_instances = set()

        # create union-find data structures to keep track of equivalent gates and nets
        self.uf_nets = UnionFind()
        for net in self.nets:
            self.uf_nets.add(net.name)
        self.uf_instances = UnionFind()
        for gate in self.gates:
            self.uf_instances.add(gate.instance)

    def find_buf_inv_chains(self):
        """collect equivalent nets from chains of buffers and inverters (to merge later)"""

        stack = list(self.output_nets)
        visited = set(stack)
        while stack:
            net = stack.pop()
            if net in self.input_nets:
                assert self.lu_net_input[net] is None
                continue
            inst = self.lu_net_input[net]
            assert inst is not None
            gate = self.lu_inst_gate[inst]
            deps = self.lu_inst_inputs[inst]
            if gate.name == GT.BUF:
                (dep,) = deps
                self.uf_nets.union(dep, net)
                self.deleted_instances.add(inst)
            elif gate.name == GT.INV:
                (dep,) = deps
                while dep not in self.input_nets:
                    inst2 = self.lu_net_input[dep]
                    assert inst2 is not None
                    gate2 = self.lu_inst_gate[inst2]
                    deps2 = self.lu_inst_inputs[inst2]
                    if gate2.name == GT.BUF:
                        (dep,) = deps2
                        continue
                    elif gate2.name == GT.INV:
                        (dep2,) = deps2
                        self.uf_nets.union(dep2, net)
                        self.deleted_instances.add(inst)
                        break
                    else:
                        break
            for dep in deps:
                if dep not in visited:
                    stack.append(dep)
                    visited.add(dep)

    def find_duplicate_gates(self):
        """find gates with identical function and inputs (to merge later)"""

        sig_lookup = {}
        nets_to_merge = []
        for gate in self.gates:
            inst = gate.instance
            if inst in self.deleted_instances:
                continue
            in_terms = sorted(k for k in gate.terminals.keys() if k in GATE_INPUTS)
            signature = [gate.name]
            for k in in_terms:
                signature.append(self.uf_nets.find(gate.terminals[k].name))
            signature = tuple(signature)
            if signature in sig_lookup:
                other_inst = sig_lookup[signature]
                other_gate = self.lu_inst_gate[other_inst]
                self.uf_instances.union(other_inst, inst)
                # dict_keys equality needs set() in micropython
                assert set(gate.terminals.keys()) == set(other_gate.terminals.keys())
                for k in gate.terminals.keys():
                    net = self.uf_nets.find(gate.terminals[k].name)
                    other_net = self.uf_nets.find(other_gate.terminals[k].name)
                    if net != other_net:
                        nets_to_merge.append((net, other_net))
            else:
                sig_lookup[signature] = inst
        for net1, net2 in nets_to_merge:
            self.uf_nets.union(net1, net2)

    def cleanup_end(self):
        """clean-up steps to run after collecting steps of equivalent nets"""

        assert self.continuous_assignments == {}

        # perform the merge on nets marked as equivalent, finding the best representative from each bucket
        self.nets = []
        reps = {}
        for s in self.uf_nets.sets():
            inputs = []
            outputs = []
            internal = []
            for net in s:
                if net in self.input_nets or net in ("$net_0", "$net_1"):
                    inputs.append(net)
                elif net in self.output_nets:
                    outputs.append(net)
                else:
                    internal.append(net)
            assert len(inputs) <= 1
            rep = None
            if inputs:
                rep = inputs[0]
            elif internal:
                rep = internal[0]
            if rep is None:
                rep = self.create_net().name
            else:
                self.nets.append(NetNode(name=rep))
            for net in s:
                reps[net] = rep
            for net in outputs:
                self.nets.append(NetNode(name=net))
                self.continuous_assignments[net] = NetNode(name=rep)

        # perform the merge on instances marked as equivalent
        self.gates = []
        for s in self.uf_instances.sets():
            s = [i for i in s if i not in self.deleted_instances]
            if not s:
                continue
            inst = s[0]
            gate = self.lu_inst_gate[inst]
            new_terminals = {}
            for k, v in gate.terminals.items():
                new_terminals[k] = NetNode(name=reps[v.name])
            new_gate = GateNode(name=gate.name, instance=inst, terminals=new_terminals)
            self.gates.append(new_gate)

        # we added continuous assignments for the outputs, replace them with buffers once again
        # so that we don't need to deal with assignments in place & route
        self.convert_assignments_to_buffers()

    def process_module(self, node):
        # props: name, ports, symbols, nets, net_counter, inst_counter, gates, continuous_assignments, body
        assert node.body == []
        self.ports = node.ports
        self.symbols = node.symbols
        self.nets = node.nets
        self.net_counter = node.net_counter
        self.inst_counter = node.inst_counter
        self.gates = node.gates
        try:
            self.continuous_assignments = node.continuous_assignments
        except AttributeError:
            self.continuous_assignments = {}

        self.cleanup_start()
        self.find_buf_inv_chains()

        cleanup_steps_max = self.config["synth.cleanup_steps_max"]
        counter = 0
        last_complexity = None
        while True:
            counter += 1
            if counter > cleanup_steps_max:
                raise RuntimeError(
                    f"Clean-up didn't converge in {cleanup_steps_max} steps, update config to override"
                )
            self.find_duplicate_gates()
            complexity = len(self.uf_instances.sets())
            if last_complexity is not None and complexity >= last_complexity:
                break
            last_complexity = complexity

        self.cleanup_end()

        ports = self.ports
        symbols = self.symbols
        nets = self.nets
        net_counter = self.net_counter
        inst_counter = self.inst_counter
        gates = self.gates
        continuous_assignments = self.continuous_assignments
        return ModuleNode(
            name=node.name,
            ports=ports,
            symbols=symbols,
            nets=nets,
            gates=gates,
            continuous_assignments=continuous_assignments,
            net_counter=net_counter,
            inst_counter=inst_counter,
        )

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
        return self.pass_through(node)
