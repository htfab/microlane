# Breaks words into bits and converts combinational expressions to logic gates

from ..util.logic import GT, BooleanOp, bit_const, bit_one, bit_zero
from ..util.nodes import (
    AssignmentStatementNode,
    BinaryExpressionNode,
    BitNode,
    BusNode,
    ConditionalStatementNode,
    DeclarationNode,
    DontCareNode,
    ForStatementNode,
    ModuleNode,
    NetNode,
    NodeProcessor,
    NullStatementNode,
    NumericNode,
    PortNode,
    RangeNode,
    RepeatStatementNode,
    ScopedBusNode,
    SequentialBlockNode,
    SymbolNode,
    WhileStatementNode,
)


class BitBlaster(NodeProcessor):
    """synthesis step converting multi-bit buses into individual bits

    - replaces a multi-bit identifier `id` with `id[0]`, `id[1]` etc.
    - resolves constant indexing, concatenation and replication
    - replaces non-constant indexing with a mux
    - implements operators as combinational networks of logic gates
    """

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        BooleanOp.configure(self.config)
        return self.pass_through(node)

    def process_module(self, node):
        # props: name, ports, body
        self.symbols = {}  # use empty symbol table while processing constants in ports & declarations
        symbols = {}
        for e in node.ports:
            if e.name in symbols:
                raise SyntaxError(f"Port {e.name} was already declared")
            symbols[e.name] = self.create_symbol(e)
        for e in node.body:
            if isinstance(e, DeclarationNode):
                if e.name in symbols:
                    prev = symbols[e.name]
                    if isinstance(prev, PortNode) and prev.direction is None:
                        raise NotImplementedError(
                            "Only Verilog-2001 style port declarations are supported at this time"
                        )
                    else:
                        raise SyntaxError(f"Signal {e.name} was already declared")
                symbols[e.name] = self.create_symbol(e)
        self.symbols = symbols  # make symbol table available to all sub-nodes
        self.nets = []
        for sym in symbols:
            self.nets.extend(self.bus_bits(self.get_symbol_nets(sym)))
        self.net_counter = 0
        self.inst_counter = 0
        self.gates = []
        self.create_gate(GT.TIELO, LO=self.create_net())  # $net_0
        self.create_gate(GT.TIEHI, HI=self.create_net())  # $net_1
        self.continuous_assignments = {}
        ports = [self.process(e) for e in node.ports]
        proc_body = [self.process(e) for e in node.body]
        body = [e for e in proc_body if e is not None]
        # save symbols for later synthesis steps,  but don't keep them outside the module
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

    def create_symbol(self, node):
        """create an entry for a port or declaration node to be stored in the module symbol table"""
        # props for ports: name, direction, signed, data_type, index
        # props for declarations: name, signed, data_type, index, assignment
        if node.index is None:
            index = None
        else:
            r = self.process(node.index)
            if isinstance(r, RangeNode):
                index = self.resolve_constant_range(r)
            else:
                raise SyntaxError(f"Invalid index for declaration: {node}")
        return SymbolNode(
            name=node.name,
            signed=node.signed,
            data_type=node.data_type,
            index=index,
        )

    def process_port(self, node):
        # props: name, direction, signed, data_type, range
        # signed, data_type and range are already stored in symbols, so we don't need them here
        return PortNode(name=node.name, direction=node.direction)

    def resolve_constant(self, node):
        """convert a (processed) expression that is a numeric constant into a Python number"""
        if isinstance(node, NumericNode):
            return node.value
        elif isinstance(node, BitNode):
            return node.value
        elif isinstance(node, BusNode) and all(
            isinstance(i, BitNode) for i in node.bits
        ):
            value = node.bits[0].value
            if node.signed:
                value = -value
            for b in node.bits[1:]:
                value <<= 1
                value |= b.value
            return value
        else:
            raise SyntaxError(f"Expected a constant instead of {node}")

    def resolve_range_operator(self, node, left, operator, right, ascending=None):
        """map Verilog-style range description to Python range, e.g. (5, "+:", 3) => range(7, 4, -1)"""
        assert ascending in (None, False, True)
        if operator == ":":
            if ascending is None:
                if left >= right:
                    return range(left, right - 1, -1)
                else:
                    return range(left, right + 1)
            elif not ascending:
                if left < right:
                    raise SyntaxError(f"Unexpected bit order in range: {node}")
                return range(left, right - 1, -1)
            elif ascending:
                if left > right:
                    raise SyntaxError(f"Unexpected bit order in range: {node}")
                return range(left, right + 1)
        elif operator == "+:":
            if ascending is None:
                raise SyntaxError(
                    f"Indexed part-select with ambiguous bit order: {node}"
                )
            elif not ascending:
                return range(left + right - 1, left - 1, -1)
            elif ascending:
                return range(left, left + right)
        elif operator == "-:":
            if ascending is None:
                raise SyntaxError(
                    f"Indexed part-select with ambiguous bit order: {node}"
                )
            elif not ascending:
                return range(left, left - right, -1)
            elif ascending:
                return range(left - right + 1, left + 1)

    def resolve_constant_range(self, node, ascending=None):
        """convert a (processed) expression that is a range constant into a Python range object"""
        assert isinstance(node, RangeNode)
        assert len(node.indices) == 2
        left, right = (self.resolve_constant(e) for e in node.indices)
        return self.resolve_range_operator(node, left, node.operator, right, ascending)

    def process_range(self, node):
        # props: indices
        return self.pass_through(node)

    def process_numeric(self, node):
        # props: value, signed, size
        size = node.size if node.size is not None else 32
        value = node.value
        bits = []
        for i in range(size - 1):
            bits.append(value & 1)
            value >>= 1
        if (value in (0, -1)) if node.signed else (value in (0, 1)):
            bits.append(value & 1)
        else:
            raise SyntaxError(f"Constant doesn't fit into specified width: {node}")
        bits = [bit_const(i) for i in reversed(bits)]
        assert len(bits) == size
        return BusNode(signed=node.signed, bits=bits)

    def process_identifier(self, node):
        # props: name
        return self.get_symbol_nets(node.name)

    def process_hierarchical_identifier(self, node):
        # props: parent, name
        raise NotImplementedError(
            "Hierarchical identifiers are not supported for the time being"
        )

    def get_symbol_nets(self, name, index=None, dont_care=False):
        """find the net or nets corresponding to an identifier, optionally indexed by a number or a range"""
        try:
            symbol = self.symbols[name]
        except KeyError:
            raise SyntaxError(
                f"Undeclared identifier (assuming default_nettype none): {name}"
            ) from None
        if symbol.index is None:
            if index is not None:
                raise SyntaxError(f"Cannot index into scalar identifier: {name}")
            return NetNode(name=name)
        else:
            if index is None:
                index_range = symbol.index
            elif isinstance(index, range):
                index_range = index
            else:
                index_range = range(index, index + 1)
            nets = []
            for i in index_range:
                if i in symbol.index:
                    nets.append(NetNode(name=f"{name}[{i}]"))
                elif dont_care:
                    nets.append(dont_care)
                else:
                    raise SyntaxError(f"Index {index} out of bounds for symbol {name}")
            if index is not None and not isinstance(index, range):
                assert len(nets) == 1
                return nets[0]
            else:
                signed = symbol.signed if index is None else False
                return BusNode(signed=signed, bits=nets)

    def bit_is_const(self, arg):
        return isinstance(arg, BitNode) or isinstance(arg, DontCareNode)

    def bit_inv(self, arg):
        return BooleanOp.inv(arg).generate(self)

    def bit_and(self, arg1, arg2):
        return BooleanOp.and2(arg1, arg2).generate(self)

    def bit_nand(self, arg1, arg2):
        return BooleanOp.nand2(arg1, arg2).generate(self)

    def bit_or(self, arg1, arg2):
        return BooleanOp.or2(arg1, arg2).generate(self)

    def bit_nor(self, arg1, arg2):
        return BooleanOp.nor2(arg1, arg2).generate(self)

    def bit_xor(self, arg1, arg2):
        return BooleanOp.xor2(arg1, arg2).generate(self)

    def bit_xnor(self, arg1, arg2):
        return BooleanOp.xnor2(arg1, arg2).generate(self)

    def bit_less(self, arg1, arg2):
        return BooleanOp.less(arg1, arg2).generate(self)

    def bit_less_or_equal(self, arg1, arg2):
        return BooleanOp.less_or_equal(arg1, arg2).generate(self)

    def bit_greater(self, arg1, arg2):
        return BooleanOp.greater(arg1, arg2).generate(self)

    def bit_greater_or_equal(self, arg1, arg2):
        return BooleanOp.greater_or_equal(arg1, arg2).generate(self)

    def bit_symbolic_binary_op(self, op, arg1, arg2):
        return BooleanOp.symbolic_binary(op, arg1, arg2).generate(self)

    def bit_reduction_op(self, op, bits):
        base_op = op
        inverting_op = op in ("~&", "~|", "~^", "^~")
        if inverting_op:
            base_op = {"~&": "&", "~|": "|", "~^": "^", "^~": "^"}[op]
        if len(bits) == 0:
            raise SyntaxError(
                f"Reduction operator needs at least one bit of input: {op}"
            )
        elif len(bits) == 1:
            if inverting_op:
                return self.bit_inv(bits[0])
            else:
                return bits[0]
        elif len(bits) == 2:
            return self.bit_symbolic_binary_op(op, bits[0], bits[1])
        split = len(bits) // 2
        arg1 = self.bit_reduction_op(base_op, bits[:split])
        arg2 = self.bit_reduction_op(base_op, bits[split:])
        return self.bit_symbolic_binary_op(op, arg1, arg2)

    def bit_mux(self, selector, val0, val1):
        return BooleanOp.mux(selector, val0, val1).generate(self)

    def bit_half_adder(self, arg1, arg2):
        return BooleanOp.ha(arg1, arg2).generate(self)

    def bit_half_adder_plus_one(self, arg1, arg2):
        return BooleanOp.hap(arg1, arg2).generate(self)

    def bit_full_adder(self, arg1, arg2, arg3):
        return BooleanOp.fa(arg1, arg2, arg3).generate(self)

    def bit_vector_increment(self, bits):
        if len(bits) == 0:
            raise SyntaxError("Increment operator needs at least one bit of input")
        elif len(bits) == 1:
            return [self.bit_inv(bits[0])]
        carry = bits[-1]
        current_bit = self.bit_inv(bits[-1])
        result = [current_bit]
        for arg in reversed(bits[1:-1]):
            carry, current_bit = self.bit_half_adder(arg, carry)
            result.append(current_bit)
        current_bit = self.bit_xor(bits[0], carry)
        result.append(current_bit)
        return list(reversed(result))

    def bit_vector_ones_complement(self, bits):
        return [self.bit_inv(e) for e in bits]

    def bit_vector_twos_complement(self, bits):
        if len(bits) == 0:
            raise SyntaxError(
                "Twos complement operator needs at least one bit of input"
            )
        return self.bit_vector_increment(self.bit_vector_ones_complement(bits))

    def process_unary_expression(self, node):
        # props: operator, argument
        op = node.operator
        arg = self.process(node.argument)
        assert any(isinstance(arg, i) for i in (NetNode, BitNode, BusNode))
        if op == "+":
            return arg
        elif op == "-":
            if isinstance(arg, BusNode):
                return BusNode(
                    signed=arg.signed, bits=self.bit_vector_twos_complement(arg.bits)
                )
            else:
                return arg
        elif op == "!":
            if isinstance(arg, BusNode):
                if len(arg.bits) == 1:
                    arg = arg.bits[0]
                else:
                    raise SyntaxError(
                        f"Logical negation only defined for a single bit, found: {node}"
                    )
            return self.bit_inv(arg)
        elif op == "~":
            if isinstance(arg, BusNode):
                return BusNode(
                    signed=False, bits=self.bit_vector_ones_complement(arg.bits)
                )
            else:
                return self.bit_inv(arg)
        elif op in ("&", "~&", "|", "~|", "^", "~^", "^~"):
            if isinstance(arg, BusNode):
                bits = arg.bits
            else:
                bits = [arg]
            return self.bit_reduction_op(op, bits)
        else:
            raise SyntaxError(f"Unexpected unary operator: {node}")

    def bit_vector_add(self, arg1, arg2, carry_in=False):
        """ripple-carry adder"""
        assert len(arg1) == len(arg2)
        if len(arg1) == 0:
            return []
        elif len(arg1) == 1:
            if carry_in:
                return [self.bit_xnor(arg1[0], arg2[0])]
            else:
                return [self.bit_xor(arg1[0], arg2[0])]
        if carry_in:
            carry, current_bit = self.bit_half_adder_plus_one(arg1[-1], arg2[-1])
        else:
            carry, current_bit = self.bit_half_adder(arg1[-1], arg2[-1])
        result = [current_bit]
        for bit1, bit2 in zip(reversed(arg1[1:-1]), reversed(arg2[1:-1])):
            carry, current_bit = self.bit_full_adder(bit1, bit2, carry)
            result.append(current_bit)
        current_bit = self.bit_xor(self.bit_xor(arg1[0], arg2[0]), carry)
        result.append(current_bit)
        return list(reversed(result))

    def bit_vector_subtract(self, arg1, arg2):
        assert len(arg1) == len(arg2)
        return self.bit_vector_add(
            arg1, self.bit_vector_ones_complement(arg2), carry_in=True
        )

    def bit_vector_equal(self, arg1, arg2):
        assert len(arg1) == len(arg2)
        bitwise_xor = [self.bit_xor(e1, e2) for e1, e2 in zip(arg1, arg2)]
        return self.bit_reduction_op("~|", bitwise_xor)

    def bit_vector_not_equal(self, arg1, arg2):
        assert len(arg1) == len(arg2)
        bitwise_xor = [self.bit_xor(e1, e2) for e1, e2 in zip(arg1, arg2)]
        return self.bit_reduction_op("|", bitwise_xor)

    def bit_vector_less(self, arg1, arg2, signed=False, allow_equal=False):
        assert len(arg1) == len(arg2)
        if len(arg1) == 0:
            return bit_one if allow_equal else bit_zero
        elif len(arg1) == 1:
            if signed:
                arg1, arg2 = arg2, arg1
            if allow_equal:
                return self.bit_less_or_equal(arg1[0], arg2[0])
            else:
                return self.bit_less(arg1[0], arg2[0])
        if signed:
            msb1, msb2 = arg2[0], arg1[0]
        else:
            msb1, msb2 = arg1[0], arg2[0]
        msb_less = self.bit_less(msb1, msb2)
        msb_less_or_equal = self.bit_less_or_equal(msb1, msb2)
        rest_less = self.bit_vector_less(
            arg1[1:], arg2[1:], signed=False, allow_equal=allow_equal
        )
        return self.bit_or(msb_less, self.bit_and(msb_less_or_equal, rest_less))

    def bit_vector_less_or_equal(self, arg1, arg2, signed=False):
        return self.bit_vector_less(arg1, arg2, signed=signed, allow_equal=True)

    def bit_vector_bitwise_op(self, op, arg1, arg2):
        assert len(arg1) == len(arg2)
        return [self.bit_symbolic_binary_op(op, e1, e2) for e1, e2 in zip(arg1, arg2)]

    def bit_vector_binary_symbolic_op(self, node, op, arg1, arg2, signed=False):
        if op == "+":
            return self.bit_vector_add(arg1, arg2)
        elif op == "-":
            return self.bit_vector_subtract(arg1, arg2)
        elif op == "*":
            raise NotImplementedError(f"Multiplication is not implemented: {node}")
        elif op == "/":
            raise NotImplementedError(f"Division is not implemented: {node}")
        elif op == "%":
            raise NotImplementedError(f"Division is not implemented: {node}")
        elif op == "**":
            raise NotImplementedError(f"Power operator is not implemented: {node}")
        elif op == "==" or op == "===":
            return self.bit_vector_equal(arg1, arg2)
        elif op == "!=" or op == "!==":
            return self.bit_vector_not_equal(arg1, arg2)
        elif op == "<":
            return self.bit_vector_less(arg1, arg2, signed)
        elif op == "<=":
            return self.bit_vector_less_or_equal(arg1, arg2, signed)
        elif op == ">":
            return self.bit_vector_less(arg2, arg1, signed)
        elif op == ">=":
            return self.bit_vector_less_or_equal(arg2, arg1, signed)
        elif op in ("&", "|", "^", "^~", "~^"):
            return self.bit_vector_bitwise_op(op, arg1, arg2)
        else:
            raise SyntaxError(f"Unexpected binary operator: {op}")

    def bit_vector_shift_left_by_constant(self, arg, amount, shift_in):
        return (arg + [shift_in] * amount)[amount:]

    def bit_vector_shift_right_by_constant(self, arg, amount, shift_in):
        return ([shift_in] * amount + arg)[:-amount]

    def bit_vector_shift_by_constant(self, arg, op, amount, shift_in):
        assert op in ("<<", "<<<", ">>", ">>>")
        if op in ("<<", "<<<"):
            return self.bit_vector_shift_left_by_constant(arg, amount, shift_in)
        elif op in (">>", ">>>"):
            return self.bit_vector_shift_right_by_constant(arg, amount, shift_in)

    def bit_vector_mux(self, selector, val0, val1):
        bits = []
        for val0_bit, val1_bit in zip(val0, val1):
            bits.append(self.bit_mux(selector, val0_bit, val1_bit))
        return bits

    def bit_vector_shift_by_non_constant(self, arg, op, amount, shift_in):
        if len(amount) > 0:
            cond0 = arg
            cond1 = self.bit_vector_shift_by_constant(
                arg, op, 1 << (len(amount) - 1), shift_in
            )
            partial = self.bit_vector_mux(amount[0], cond0, cond1)
            return self.bit_vector_shift_by_non_constant(
                partial, op, amount[1:], shift_in
            )
        else:
            return arg

    def process_binary_expression(self, node):
        # props: operator, arguments
        op = node.operator
        arg1, arg2 = (self.process(e) for e in node.arguments)
        if op in ("+", "-", "*", "/", "%", "**"):
            signed = self.bus_all_signed(arg1, arg2)
            arg1_bits, arg2_bits = self.bus_bits_longest(arg1, arg2, signed=signed)
            bits = self.bit_vector_binary_symbolic_op(
                node, op, arg1_bits, arg2_bits, signed=signed
            )
            return BusNode(signed=signed, bits=bits)
        elif op in ("==", "!==", "===", "!==", "<", "<=", ">", ">="):
            signed = self.bus_all_signed(arg1, arg2)
            arg1_bits, arg2_bits = self.bus_bits_longest(arg1, arg2, signed=signed)
            return self.bit_vector_binary_symbolic_op(
                node, op, arg1_bits, arg2_bits, signed=signed
            )
        elif op in ("&", "|", "^", "^~", "~^"):
            arg1_bits, arg2_bits = self.bus_bits_longest(arg1, arg2, signed=False)
            bits = self.bit_vector_binary_symbolic_op(
                node, op, arg1_bits, arg2_bits, signed=False
            )
            return BusNode(signed=False, bits=bits)
        elif op == "&&":
            return self.bit_and(self.bus_to_bit(arg1), self.bus_to_bit(arg2))
        elif op == "||":
            return self.bit_or(self.bus_to_bit(arg1), self.bus_to_bit(arg2))
        elif op in (">>", "<<", ">>>", "<<<"):
            signed = self.bus_all_signed(arg1)
            arg_bits = self.bus_bits(arg1)
            shift_in = bit_zero
            if signed and op == ">>>":
                shift_in = arg_bits[0]
            if self.bus_is_const(node.arguments[1]):
                amount = self.resolve_constant(node.arguments[1])
                bits = self.bit_vector_shift_by_constant(arg_bits, op, amount, shift_in)
            else:
                amount = self.bus_bits(arg2)
                bits = self.bit_vector_shift_by_non_constant(
                    arg_bits, op, amount, shift_in
                )
            return BusNode(signed=signed, bits=bits)
        else:
            raise SyntaxError(f"Unexpected binary operator: {node}")

    def bus_max_len(self, *buses):
        """returns length of the longest argument"""
        max_len = 0
        for bus in buses:
            if isinstance(bus, BusNode):
                cur_len = len(bus.bits)
            elif any(isinstance(bus, i) for i in (BitNode, NetNode, DontCareNode)):
                cur_len = 1
            else:
                raise SyntaxError("Unexpected bus: {node}")
            if cur_len > max_len:
                max_len = cur_len
        return max_len

    def bus_bits(self, bus):
        """returns the bits of a bus, also handling single-bit nets"""
        if isinstance(bus, BusNode):
            return bus.bits
        elif any(isinstance(bus, i) for i in (BitNode, NetNode, DontCareNode)):
            return [bus]

    def bus_is_const(self, bus):
        """returns whether all bits in the bus are constant"""
        return all(self.bit_is_const(bit) for bit in self.bus_bits(bus))

    def bus_bits_extended(self, bus, length, signed=None):
        """returns the bits of a bus, sign-extended to a given length"""
        if isinstance(bus, BusNode):
            bits = bus.bits
            if signed is None:
                signed = bus.signed
        elif any(isinstance(bus, i) for i in (BitNode, NetNode, DontCareNode)):
            bits = [bus]
            if signed is None:
                signed = False
        else:
            raise SyntaxError("Unexpected bus: {node}")
        if len(bits) == length:
            return bits
        elif len(bits) < length:
            if signed:
                extension_bit = bits[0]
            else:
                extension_bit = bit_zero
            return [extension_bit] * (length - len(bits)) + bits
        else:
            raise RuntimeError(
                "Bus sign-extension requested, refusing to truncate: {bus}"
            )

    def bus_resized_to_other(self, bus, reference, signed=None):
        """resizes the first bus so that it has the same length as the reference"""
        bus_bits = self.bus_bits(bus)
        ref_bits = self.bus_bits(reference)
        bus_len = len(bus_bits)
        ref_len = len(ref_bits)
        if bus_len == ref_len:
            return bus
        if signed is None:
            signed = bus.signed if isinstance(bus, BusNode) else False
        if bus_len < ref_len:
            bits = self.bus_bits_extended(bus, ref_len, signed=signed)
        elif bus_len > ref_len:
            bits = bus_bits[-ref_len:]
        return BusNode(signed=signed, bits=bits)

    def bus_all_signed(self, *buses):
        """returns whether all the inputs are signed"""
        all_signed = True
        for bus in buses:
            if not (isinstance(bus, BusNode) and bus.signed):
                all_signed = False
        return all_signed

    def bus_bits_longest(self, *buses, signed=None):
        """returns bit lists for all buses, extended to the longest"""
        max_len = self.bus_max_len(*buses)
        return [self.bus_bits_extended(bus, max_len, signed=signed) for bus in buses]

    def bus_mux(self, selector, val0, val1):
        """returns the bits of (selector ? val1 : val0) where selector is a single net"""
        signed = self.bus_all_signed(val0, val1)
        val0_bits, val1_bits = self.bus_bits_longest(val0, val1, signed=signed)
        bits = self.bit_vector_mux(selector, val0_bits, val1_bits)
        return BusNode(signed=signed, bits=bits)

    def bus_to_bit(self, bus):
        """returns a net corresponding to the logic value of a bus (i.e. whether it is nonzero)"""
        if isinstance(bus, BusNode):
            return self.bit_reduction_op("&", bus.bits)
        elif any(isinstance(bus, i) for i in (BitNode, NetNode, DontCareNode)):
            return bus
        else:
            raise RuntimeError(f"Expected bus or net, found: {bus}")

    def process_conditional_expression(self, node):
        # props: arguments
        condition, branch1, branch0 = (self.process(e) for e in node.arguments)
        condition = self.bus_to_bit(condition)
        if isinstance(branch0, BusNode) or isinstance(branch1, BusNode):
            return self.bus_mux(condition, branch0, branch1)
        else:
            return self.bit_mux(condition, branch0, branch1)

    def index_offset(self, index, offset):
        """add a number to a Python range (or another number)"""
        if isinstance(index, range):
            return range(index.start + offset, index.stop + offset, index.step)
        else:
            return index + offset

    def recurse_non_constant_index(self, name, index_bits, index):
        """creates the mux structure for indexing by a non-constant value"""
        if len(index_bits) > 0:
            cond0 = self.recurse_non_constant_index(name, index_bits[1:], index)
            cond1 = self.recurse_non_constant_index(
                name,
                index_bits[1:],
                self.index_offset(index, 1 << (len(index_bits) - 1)),
            )
            if isinstance(cond0, BusNode):
                assert isinstance(cond1, BusNode)
                return self.bus_mux(index_bits[0], cond0, cond1)
            else:
                assert not isinstance(cond1, BusNode)
                return self.bit_mux(index_bits[0], cond0, cond1)
        else:
            return self.get_symbol_nets(name, index, dont_care=True)

    def process_index_expression(self, node):
        # props: identifier, index
        name = node.identifier.name
        symbol = self.symbols[name]
        index_node = self.process(node.index)
        if self.bus_is_const(node.index):
            if isinstance(index_node, RangeNode):
                index_range = self.resolve_constant_range(
                    index_node, ascending=(symbol.range.step > 0)
                )
                return self.get_symbol_nets(name, index_range)
            else:
                index_val = self.resolve_constant(index_node)
                return self.get_symbol_nets(name, index_val)
        else:
            if isinstance(index_node, RangeNode):
                base_node = index_node.indices[0]
            else:
                base_node = index_node
            if not isinstance(base_node, BusNode):
                index_bits = [base_node]
                start_index = 0
            elif base_node.signed:
                index_bits = base_node.bits
                start_index = -(1 << (len(index_bits) - 1))
            else:
                index_bits = base_node.bits
                start_index = 0
            if isinstance(index_node, RangeNode):
                left, right = start_index, self.resolve_constant(index_node.indices[1])
                start_index = self.resolve_range_operator(
                    index_node,
                    left,
                    index_node.operator,
                    right,
                    ascending=(symbol.range.step > 0),
                )
            return self.recurse_non_constant_index(name, index_bits, start_index)

    def bus_concatenate(self, expressions):
        bits = []
        for expr in expressions:
            proc_expr = self.process(expr)
            assert any(isinstance(proc_expr, i) for i in (NetNode, BitNode, BusNode))
            if isinstance(proc_expr, BusNode):
                bits.extend(proc_expr.bits)
            else:
                bits.append(proc_expr)
        return bits

    def process_concatenation(self, node):
        # props: expressions
        bits = self.bus_concatenate(node.expressions)
        return BusNode(signed=False, bits=bits)

    def process_replication(self, node):
        # props: repeat, expressions
        repeat = self.resolve_constant(self.process(node.repeat))
        bits = repeat * self.bus_concatenate(node.expressions)
        return BusNode(signed=False, bits=bits)

    def add_continuous_assignment(self, node, lhs, rhs):
        rhs_resized = self.bus_resized_to_other(rhs, lhs)
        lhs_bits = self.bus_bits(lhs)
        rhs_bits = self.bus_bits(rhs_resized)
        assert len(lhs_bits) == len(rhs_bits)
        for lb, rb in zip(lhs_bits, rhs_bits):
            assert isinstance(lb, NetNode)
            name = lb.name
            if name in self.continuous_assignments:
                raise NotImplementedError(
                    f"Multiple drivers for single net not implemented, but {name} is assigned again in {node}"
                )
            self.continuous_assignments[name] = rb

    def process_declaration(self, node):
        # props: name, signed, data_type, range, assignment
        # we only need the assignment here, the declaration was already processed for the symbol table
        if node.assignment is None:
            # declaration only, e.g. "wire a;"
            return None
        else:
            # combined declaration and assignment, e.g. "wire a = b;"
            lhs = self.get_symbol_nets(node.name)
            rhs = self.process(node.assignment)
            self.add_continuous_assignment(node, lhs, rhs)
            return None

    def process_continuous_assignment(self, node):
        # props: lhs, rhs
        lhs = self.process(node.lhs)
        rhs = self.process(node.rhs)
        self.add_continuous_assignment(node, lhs, rhs)
        return None

    def process_always_block(self, node):
        # props: block_type, sensitivity_list, statement
        return self.pass_through(node)

    def process_event_expression(self, node):
        # props: edge, expression
        return self.pass_through(node)

    def flatten_sequential_blocks(self, statements):
        """in a list of sequential statements, replace a begin...end block with its contents"""
        result = []
        for st in statements:
            if isinstance(st, SequentialBlockNode):
                result.extend(st.statements)
            else:
                result.append(st)
        return result

    def process_sequential_block(self, node):
        # props: statements
        statements = [self.process(st) for st in node.statements]
        return SequentialBlockNode(
            statements=self.flatten_sequential_blocks(statements)
        )

    def gate_scope(self):
        """returns a context manager for creating gates in a local scope, not directly in the module"""

        class GateScope:
            def __init__(self, node_processor):
                self.node_processor = node_processor

            def __enter__(self):
                self.saved_gates = self.node_processor.gates
                self.node_processor.gates = []

            def __exit__(self, exception_type, exception_value, traceback):
                self.gates = self.node_processor.gates
                self.node_processor.gates = self.saved_gates

            def resolve(self, node):
                signed = isinstance(node, BusNode) and node.signed
                bits = self.node_processor.bus_bits(node)
                return ScopedBusNode(gates=self.gates, signed=signed, bits=bits)

        return GateScope(self)

    def scoped_process(self, node):
        scope = self.gate_scope()
        with scope:
            result = self.process(node)
        return scope.resolve(result)

    def process_conditional_statement(self, node):
        # props: condition, branch1, branch0
        condition = self.scoped_process(node.condition)
        branch1 = self.process(node.branch1)
        branch0 = self.process(node.branch0)
        return ConditionalStatementNode(
            condition=condition, branch1=branch1, branch0=branch0
        )

    def process_case_statement(self, node):
        # props: expression, cases
        # (we need to convert a case statement into if statements during bit blasting since we might
        #  have to sign-extend the case expression to different lengths depending on the case item)
        non_default_cases = [e for e in node.cases if e.matches != "default"]
        default_cases = [e for e in node.cases if e.matches == "default"]
        if len(default_cases) == 0:
            default_branch = NullStatementNode()
        elif len(default_cases) == 1:
            default_branch = default_cases[0].branch
        else:
            raise SyntaxError(f"Case statement can only have one default item: {node}")
        if len(non_default_cases) == 0:
            return self.process(default_branch)
        first = None
        last = None
        for case in non_default_cases:
            scope = self.gate_scope()
            with scope:
                condition_bits = []
                for match_ in case.matches:
                    eq = BinaryExpressionNode(
                        operator="==", arguments=[node.expression, match_]
                    )
                    condition_bits.append(self.process(eq))
                condition = self.bit_reduction_op("|", condition_bits)
            condition = scope.resolve(condition)
            branch1 = self.process(case.branch)
            temp_branch0 = NullStatementNode()
            cs = ConditionalStatementNode(
                condition=condition, branch1=branch1, branch0=temp_branch0
            )
            if first is None:
                first = cs
            if last is not None:
                last.branch0 = cs
            last = cs
        assert first is not None
        assert last is not None
        last.branch0 = self.process(default_branch)
        return first

    def process_case_item(self, node):
        # props: matches, branch
        return self.pass_through(node)

    def process_forever_statement(self, node):
        # props: body
        return self.pass_through(node)

    def process_repeat_statement(self, node):
        # props: count, body
        count = self.scoped_process(node.count)
        body = self.process(node.body)
        return RepeatStatementNode(count=count, body=body)

    def process_while_statement(self, node):
        # props: condition, body
        condition = self.scoped_process(node.condition)
        body = self.process(node.body)
        return WhileStatementNode(condition=condition, body=body)

    def process_for_statement(self, node):
        # props: init, condition, step, body
        assert isinstance(node.init, AssignmentStatementNode)
        assert isinstance(node.step, AssignmentStatementNode)
        init = self.process(node.init)
        condition = self.scoped_process(node.condition)
        step = self.process(node.step)
        body = self.process(node.body)
        return ForStatementNode(init=init, condition=condition, step=step, body=body)

    def process_assignment_statement(self, node):
        # props: blocking, lhs, rhs
        lhs = self.process(node.lhs)
        scope = self.gate_scope()
        with scope:
            rhs = self.process(node.rhs)
            rhs = self.bus_resized_to_other(rhs, lhs)
        rhs = scope.resolve(rhs)
        lhs_bits = self.bus_bits(lhs)
        assert len(lhs_bits) == len(rhs.bits)
        assert all(isinstance(lb, NetNode) for lb in lhs_bits)
        return AssignmentStatementNode(blocking=node.blocking, lhs=lhs, rhs=rhs)

    def process_null_statement(self, node):
        # no props
        return self.pass_through(node)

    def process_gate_instantiation(self, node):
        # props: gate, input_terminals, output_terminal
        inputs = [self.process(e) for e in node.input_terminals]
        output = self.process(node.output_terminal)
        if isinstance(output, BusNode):
            for it in inputs:
                assert isinstance(it, BusNode)
                assert len(it.bits) == len(output.bits)
            instances = []
            for i in range(len(output.bits)):
                terms = [it.bits[i] for it in inputs] + [output.bits[i]]
                instances.append(terms)
        else:
            assert not any(isinstance(it, BusNode) for it in inputs)
            terms = inputs + [output]
            instances = [terms]

        for terms in instances:
            if node.gate == "buf":
                self.create_gate(GT.BUF, A=terms[0], X=terms[1])
            elif node.gate == "inv":
                self.create_gate(GT.INV, A=terms[0], Y=terms[1])
            elif node.gate == "and":
                self.create_gate(GT.AND, A=terms[0], B=terms[1], X=terms[2])
            elif node.gate == "nand":
                self.create_gate(GT.NAND, A=terms[0], B=terms[1], Y=terms[2])
            elif node.gate == "or":
                self.create_gate(GT.OR, A=terms[0], B=terms[1], X=terms[2])
            elif node.gate == "nor":
                self.create_gate(GT.NOR, A=terms[0], B=terms[1], Y=terms[2])
            elif node.gate == "xor":
                self.create_gate(GT.XOR, A=terms[0], B=terms[1], X=terms[2])
            elif node.gate == "xnor":
                self.create_gate(GT.XNOR, A=terms[0], B=terms[1], Y=terms[2])
            else:
                raise SyntaxError(f"Unknown gate {node}")

    def process_module_instantiation(self, node):
        # props: module_name, instance_name, port_connections
        return self.pass_through(node)

    def process_port_connection(self, node):
        # props: port_name, value
        return self.pass_through(node)
