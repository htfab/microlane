# Converts sequential logic (always* blocks) into logic gates

from ..util.logic import GT, BooleanOp, bit_one, bit_zero, dont_care
from ..util.nodes import (
    BitNode,
    BusNode,
    DontCareNode,
    ForStatementNode,
    ModuleNode,
    NetNode,
    Node,
    NodeProcessor,
)


class PendingAssignment:
    """keeps track of assignments to a single register bit inside an always* block"""

    def __init__(self, node_processor, template=None):
        self.node_processor = node_processor
        self.blocking_assigned = (
            bit_zero if template is None else template.blocking_assigned
        )
        self.blocking_value = bit_zero if template is None else template.blocking_value
        self.non_blocking_assigned = (
            bit_zero if template is None else template.non_blocking_assigned
        )
        self.non_blocking_value = (
            bit_zero if template is None else template.non_blocking_value
        )

    def assign(self, value, blocking):
        """process a blocking or non-blocking bit assignment"""
        if blocking:
            self.blocking_value = value
            self.blocking_assigned = bit_one
        else:
            self.non_blocking_value = value
            self.non_blocking_assigned = bit_one

    def merge(self, condition, other):
        """keep current assignments if condition is true, else switch to other (used for merging paths at the end of a conditional block)"""
        self.blocking_value = BooleanOp.mux(
            condition, other.blocking_value, self.blocking_value
        ).generate(self.node_processor)
        self.blocking_assigned = BooleanOp.mux(
            condition, other.blocking_assigned, self.blocking_assigned
        ).generate(self.node_processor)
        self.non_blocking_value = BooleanOp.mux(
            condition, other.non_blocking_value, self.non_blocking_value
        ).generate(self.node_processor)
        self.non_blocking_assigned = BooleanOp.mux(
            condition, other.non_blocking_assigned, self.non_blocking_assigned
        ).generate(self.node_processor)

    def query_blocking(self, default):
        """get current value within always* block"""
        return BooleanOp.mux(
            self.blocking_assigned, default, self.blocking_value
        ).generate(self.node_processor)

    def query_comb(self, default):
        """get value at end of always_comb block"""
        return BooleanOp.mux(
            self.non_blocking_assigned,
            self.query_blocking(default),
            self.non_blocking_value,
        ).generate(self.node_processor)

    def query_comb_valid(self):
        """returns a net that evaluates to 1 if register was assigned in all branches of an always_comb block"""
        return BooleanOp.or2(
            self.non_blocking_assigned, self.blocking_assigned
        ).generate(self.node_processor)

    def query_ff(self, clk, default):
        """get value at end of always_ff block"""
        comb = self.query_comb(default)
        if isinstance(comb, NetNode):
            return self.node_processor.create_gate(GT.DFF, "Q", CLK=clk, D=comb)
        else:
            assert isinstance(comb, BitNode) or isinstance(comb, DontCareNode)
            return comb

    def copy(self):
        return self.__class__(self.node_processor, template=self)


class SequentialState:
    """keeps track of all registers in an always* or begin..end block during elaboration"""

    def __init__(self, node_processor):
        self.node_processor = node_processor
        self.pending_assignments = {}

    def query_bits(self, bus):
        """evaluate an expression (from a scoped bus) using pending register values"""
        logic_chain_max = self.node_processor.config["synth.logic_chain_max"]
        drivers = {}
        for g in bus.gates:
            op, inputs, outputs = BooleanOp.parts_from_gate(g)
            for o in outputs:
                assert isinstance(o, NetNode)
                assert o.name not in drivers
                drivers[o.name] = (op, inputs, outputs)
        lookup = {}
        query_bits = []
        for b in bus.bits:
            if isinstance(b, BitNode) or isinstance(b, DontCareNode):
                query_bits.append(b)
                continue
            assert isinstance(b, NetNode)
            while b.name not in lookup:
                t = b
                counter = 0
                while t.name not in lookup:
                    if t.name in drivers:
                        assert t.name not in self.pending_assignments
                        op, inputs, outputs = drivers[t.name]
                        missing = next(
                            (
                                i
                                for i in inputs
                                if isinstance(i, NetNode) and i.name not in lookup
                            ),
                            None,
                        )
                        if missing is None:
                            new_inputs = [
                                (lookup[i.name] if isinstance(i, NetNode) else i)
                                for i in inputs
                            ]
                            new_outputs = op(*new_inputs).generate(self.node_processor)
                            if isinstance(new_outputs, Node):
                                new_outputs = [new_outputs]
                            for o, no in zip(outputs, new_outputs):
                                lookup[o.name] = no
                            assert t.name in lookup
                        else:
                            t = missing
                            counter += 1
                            if counter > logic_chain_max:
                                raise RuntimeError(
                                    f"Logic chain longer than {logic_chain_max}, update config to override: {b}"
                                )
                    elif t.name in self.pending_assignments:
                        lookup[t.name] = self.pending_assignments[
                            t.name
                        ].query_blocking(t)
                    else:
                        lookup[t.name] = t
            query_bits.append(lookup[b.name])
        return query_bits

    def query_bit(self, bus):
        """evaluate a single-bit expression (from a scoped bus)"""
        bits = self.query_bits(bus)
        assert len(bits) == 1
        return bits[0]

    def resolve_constant(self, bus):
        """convert an expression (already processed into as scoped bus) to a Python number"""
        bits = self.query_bits(bus)
        if all(isinstance(i, BitNode) for i in bits):
            value = bits[0].value
            if bus.signed:
                value = -value
            for b in bits[1:]:
                value <<= 1
                value |= b.value
            return value
        else:
            raise ValueError(f"Expected a constant instead of {bus}")

    def assign(self, lhs_bits, rhs_bits, blocking):
        """update pending assignments from an assignment statement"""
        for lb, rb in zip(lhs_bits, rhs_bits):
            assert isinstance(lb, NetNode)
            if lb.name not in self.pending_assignments:
                self.pending_assignments[lb.name] = PendingAssignment(
                    self.node_processor
                )
            self.pending_assignments[lb.name].assign(rb, blocking)

    def merge(self, condition, other):
        """keep current assignments if condition is true, else switch to other (used for merging paths at the end of a conditional block)"""
        for var in set(self.pending_assignments) | set(other.pending_assignments):
            try:
                self_pa = self.pending_assignments[var]
            except KeyError:
                self_pa = PendingAssignment(self.node_processor)
            try:
                other_pa = other.pending_assignments[var]
            except KeyError:
                other_pa = PendingAssignment(other.node_processor)
            self_pa.merge(condition, other_pa)
            self.pending_assignments[var] = self_pa

    def apply_comb(self):
        """converts pending assignments to continuous assignments at end of always_comb block"""
        for k, v in self.pending_assignments.items():
            assert k not in self.node_processor.continuous_assignments
            valid = v.query_comb_valid()
            if not isinstance(valid, BitNode) or valid.value != 1:
                raise RuntimeError(
                    f"Net {k} might not be assigned in every branch of an always_comb block"
                )
            self.node_processor.continuous_assignments[k] = v.query_comb(dont_care)

    def apply_ff(self, clk):
        """converts pending assignments to flip flops & continuous assignments at end of always_ff block"""
        for k, v in self.pending_assignments.items():
            assert k not in self.node_processor.continuous_assignments
            default = NetNode(name=k)
            self.node_processor.continuous_assignments[k] = v.query_ff(clk, default)

    def copy(self):
        other = self.__class__(self.node_processor)
        for k, v in self.pending_assignments.items():
            other.pending_assignments[k] = v.copy()
        return other


class Elaborator(NodeProcessor):
    """synthesis step converting always blocks to gates"""

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        BooleanOp.configure(self.config)
        return self.pass_through(node)

    def process_module(self, node):
        # props: name, ports, symbols, nets, net_counter, inst_counter, gates, continuous_assignments, body
        self.symbols = node.symbols
        self.nets = node.nets
        self.net_counter = node.net_counter
        self.inst_counter = node.inst_counter
        self.gates = node.gates
        self.continuous_assignments = node.continuous_assignments
        ports = [self.process(e) for e in node.ports]
        proc_body = [self.process(e) for e in node.body]
        body = [e for e in proc_body if e is not None]
        symbols = self.symbols
        del self.symbols
        nets = self.nets
        del self.nets
        net_counter = self.net_counter
        del self.net_counter
        inst_counter = self.inst_counter
        del self.inst_counter
        gates = self.gates
        del self.gates
        continuous_assignments = self.continuous_assignments
        del self.continuous_assignments
        return ModuleNode(
            name=node.name,
            ports=ports,
            body=body,
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

    def process_always_block(self, node):
        # props: block_type, sensitivity_list, statement
        self.sequential_state = SequentialState(self)
        self.process(node.statement)
        if node.block_type == "always":
            sl = node.sensitivity_list
            if len(sl) == 1:
                if sl[0].edge == "posedge":
                    clk = sl[0].expression
                    if isinstance(clk, NetNode):
                        self.sequential_state.apply_ff(clk)
                        del self.sequential_state
                        return
        elif node.block_type == "always_comb":
            if node.sensitivity_list is None:
                self.sequential_state.apply_comb()
                del self.sequential_state
                return
        raise NotImplementedError(
            'Only "always @(posedge clk)" and "always_comb" is implemented at this time'
        )

    def process_sequential_block(self, node):
        # props: statements
        for st in node.statements:
            self.process(st)

    def bus_bits(self, bus):
        """returns the bits of a bus, also handling single-bit nets"""
        if isinstance(bus, BusNode):
            return bus.bits
        elif any(isinstance(bus, i) for i in (BitNode, NetNode, DontCareNode)):
            return [bus]

    def process_conditional_statement(self, node):
        # props: condition, branch1, branch0
        condition = self.sequential_state.query_bit(node.condition)
        if isinstance(condition, BitNode):
            assert condition.value in (0, 1)
            if condition.value == 0:
                return self.process(node.branch0)
            elif condition.value == 1:
                return self.process(node.branch1)
        elif isinstance(condition, DontCareNode):
            return self.process(node.branch0)
        assert isinstance(condition, NetNode)
        true_state = self.sequential_state.copy()
        self.process(node.branch0)
        false_state = self.sequential_state
        self.sequential_state = true_state
        self.process(node.branch1)
        self.sequential_state.merge(condition, false_state)

    def process_forever_statement(self, node):
        # props: body
        raise RuntimeError(f"Cannot synthesize 'forever' statement: {node}")

    def process_repeat_statement(self, node):
        # props: count, body
        loop_unroll_max = self.config["synth.loop_unroll_max"]
        try:
            count = self.sequential_state.resolve_constant(node.count)
        except ValueError:
            raise ValueError(
                f"Cannot synthesize 'repeat' statement where count doesn't evaluate to a constant: {node}"
            )
        if count > loop_unroll_max:
            raise RuntimeError(
                f"Refusing to unroll loop with mode than {loop_unroll_max} iterations, update config to override: {node}"
            )
        for i in range(count):
            self.process(node.body)

    def loop_handler(self, node):
        """shared handling of "for" & "while" loops"""
        loop_unroll_max = self.config["synth.loop_unroll_max"]
        if isinstance(node, ForStatementNode):
            self.process(node.init)
        loop_count = 0
        while True:
            condition = self.sequential_state.query_bit(node.condition)
            if isinstance(condition, BitNode):
                assert condition.value in (0, 1)
                if condition.value == 0:
                    break
                elif condition.value == 1:
                    loop_count += 1
                    if loop_count > loop_unroll_max:
                        raise RuntimeError(
                            f"Refusing to unroll loop with more than {loop_unroll_max} iterations, update config to override: {node}"
                        )
                    self.process(node.body)
                    if isinstance(node, ForStatementNode):
                        self.process(node.step)
                    continue
            elif isinstance(condition, DontCareNode):
                break
            else:
                raise ValueError(
                    f"Cannot synthesize 'for' loop where condition cannot be resolved at elaboration time: {node}"
                )

    def process_while_statement(self, node):
        # props: condition, body
        self.loop_handler(node)

    def process_for_statement(self, node):
        # props: init, condition, step, body
        self.loop_handler(node)

    def process_assignment_statement(self, node):
        # props: blocking, lhs, rhs
        rhs_bits = self.sequential_state.query_bits(node.rhs)
        lhs_bits = self.bus_bits(node.lhs)
        self.sequential_state.assign(lhs_bits, rhs_bits, node.blocking)

    def process_continuous_assignment(self, node):
        # props: lhs, rhs
        return self.pass_through(node)

    def process_net(self, node):
        # props: name
        return self.pass_through(node)

    def process_bit(self, node):
        # props: value
        return self.pass_through(node)

    def process_bus(self, node):
        # props: signed, bits
        return self.pass_through(node)

    def process_gate(self, node):
        # props: name, instance, terminals
        return self.pass_through(node)
