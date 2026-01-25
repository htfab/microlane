# Utility classes for Boolean functions and combinational logic gates

from .nodes import BitNode, DontCareNode, GateNode, NetNode, assert_net_or_bit

GATE_TYPES = [
    "BUF",
    "INV",
    "AND",
    "AND_B",
    "NAND",
    "OR",
    "OR_B",
    "NOR",
    "XOR",
    "XNOR",
    "MUX",
    "HA",
    "FA",
    "TIELO",
    "TIEHI",
    "DFF",
    "DLATCH",
    "CLKGATE",
]
COMBINATIONAL_GATES = [
    "BUF",
    "INV",
    "AND",
    "AND_B",
    "NAND",
    "OR",
    "OR_B",
    "NOR",
    "XOR",
    "XNOR",
    "MUX",
    "HA",
    "FA",
    "TIELO",
    "TIEHI",
]
GATE_INPUTS = ["A", "A0", "A1", "A_N", "B", "B_N", "CIN", "CLK", "D", "GATE", "S"]
GATE_OUTPUTS = ["COUT", "GCLK", "HI", "LO", "Q", "SUM", "X", "Y"]


class GT:
    """enum for gate types"""

    pass


for t in GATE_TYPES:
    setattr(GT, t, t)
del t


bit_zero = BitNode(value=0)
bit_one = BitNode(value=1)
dont_care = DontCareNode()


def bit_const(value):
    return [bit_zero, bit_one][value]


class BooleanOpConfig:
    def __init__(self):
        self.split_mux = False
        self.split_half_adder = False
        self.split_full_adder = False

    def update(self, config):
        self.split_mux = config["synth.split_mux"]
        self.split_half_adder = config["synth.split_half_adder"]
        self.split_full_adder = config["synth.split_full_adder"]


config = BooleanOpConfig()


class BooleanOp:
    """base class for boolean operators"""

    @classmethod
    def from_gate(cls, gate):
        op, args, _ = cls.parts_from_gate(gate)
        return op(*args)

    @classmethod
    def parts_from_gate(cls, gate):
        assert isinstance(gate, GateNode)
        t = gate.terminals
        if gate.name == GT.BUF:
            return UnaryOp.buf, (t["A"],), (t["X"],)
        elif gate.name == GT.INV:
            return UnaryOp.inv, (t["A"],), (t["Y"],)
        elif gate.name == GT.AND:
            return BinaryOp.and_, (t["A"], t["B"]), (t["X"],)
        elif gate.name == GT.AND_B:
            return BinaryOp.less, (t["A_N"], t["B"]), (t["X"],)
        elif gate.name == GT.NAND:
            return BinaryOp.nand, (t["A"], t["B"]), (t["Y"],)
        elif gate.name == GT.OR:
            return BinaryOp.or_, (t["A"], t["B"]), (t["X"],)
        elif gate.name == GT.OR_B:
            return BinaryOp.greater_or_equal, (t["A"], t["B_N"]), (t["X"],)
        elif gate.name == GT.NOR:
            return BinaryOp.nor, (t["A"], t["B"]), (t["Y"],)
        elif gate.name == GT.XOR:
            return BinaryOp.xor, (t["A"], t["B"]), (t["X"],)
        elif gate.name == GT.XNOR:
            return BinaryOp.xnor, (t["A"], t["B"]), (t["Y"],)
        elif gate.name == GT.MUX:
            return MuxOp, (t["S"], t["A0"], t["A1"]), (t["X"],)
        elif gate.name == GT.HA:
            return HalfAdderOp, (t["A"], t["B"]), (t["COUT"], t["SUM"])
        elif gate.name == GT.FA:
            return FullAdderOp, (t["A"], t["B"], t["CIN"]), (t["COUT"], t["SUM"])
        elif gate.name == GT.TIELO:
            return lambda: BitConstant.zero, (), (t["LO"],)
        elif gate.name == GT.TIEHI:
            return lambda: BitConstant.one, (), (t["HI"],)
        elif gate.name in (GT.DFF, GT.DLATCH, GT.CLKGATE):
            raise ValueError(f"Expected a combinational gate: {gate}")
        else:
            raise NotImplementedError(f"Unexpected gate in BooleanOp: {gate}")

    @classmethod
    def configure(cls, new_config):
        config.update(new_config)


class BitConstant(BooleanOp):
    """boolean operator with 0 inputs"""

    def __init__(self, node):
        self.node = node

    def generate(self, np):
        return self.node

    @classmethod
    def bit(cls, value):
        return [cls.zero, cls.one][value]


BitConstant.zero = BitConstant(bit_zero)
BitConstant.one = BitConstant(bit_one)
BitConstant.dc = BitConstant(dont_care)


class UnaryOp(BooleanOp):
    """boolean operator with 1 input"""

    def __init__(self, truth_table, arg):
        self.truth_table = truth_table
        self.arg = arg

    def __new__(cls, truth_table, arg):
        self = super().__new__(cls)
        assert_net_or_bit(arg)
        if isinstance(arg, BitNode):
            return BitConstant.bit(truth_table[arg.value])
        elif truth_table[0] == truth_table[1]:
            return BitConstant.bit(truth_table[0])
        elif isinstance(arg, DontCareNode):
            return BitConstant.dc
        else:
            return self

    def generate(self, np):
        if self.truth_table == (0, 1):
            return self.arg
        elif self.truth_table == (1, 0):
            return np.create_gate(GT.INV, "Y", A=self.arg)
        else:
            raise ValueError(f"Invalid truth table in UnaryOp: {self.truth_table}")

    @classmethod
    def buf(cls, arg):
        return cls((0, 1), arg)

    @classmethod
    def inv(cls, arg):
        return cls((1, 0), arg)


class BinaryOp(BooleanOp):
    """boolean operator with 2 inputs"""

    def __init__(self, truth_table, arg1, arg2):
        self.truth_table = truth_table
        self.arg1 = arg1
        self.arg2 = arg2

    def __new__(cls, truth_table, arg1, arg2):
        self = super().__new__(cls)
        assert_net_or_bit(arg1, arg2)
        if isinstance(arg1, BitNode):
            return UnaryOp(truth_table[arg1.value], arg2)
        elif isinstance(arg2, BitNode):
            return UnaryOp(tuple(e[arg2.value] for e in truth_table), arg1)
        elif truth_table[0] == truth_table[1]:
            return UnaryOp(truth_table[0], arg2)
        elif all(e[0] == e[1] for e in truth_table):
            return UnaryOp((truth_table[0][0], truth_table[1][0]), arg1)
        elif isinstance(arg1, DontCareNode):
            if truth_table[0][0] == truth_table[1][0]:
                return BitConstant.bit(truth_table[0][0])
            elif truth_table[0][1] == truth_table[1][1]:
                return BitConstant.bit(truth_table[0][1])
            else:
                return BitConstant.dc
        elif isinstance(arg2, DontCareNode):
            if truth_table[0][0] == truth_table[0][1]:
                return BitConstant.bit(truth_table[0][0])
            elif truth_table[1][0] == truth_table[1][1]:
                return BitConstant.bit(truth_table[1][0])
            else:
                return BitConstant.dc
        else:
            return self

    def generate(self, np):
        if self.truth_table == ((0, 0), (0, 1)):
            return np.create_gate(GT.AND, "X", A=self.arg1, B=self.arg2)
        elif self.truth_table == ((0, 0), (1, 0)):
            return np.create_gate(GT.AND_B, "X", A_N=self.arg2, B=self.arg1)
        elif self.truth_table == ((0, 1), (0, 0)):
            return np.create_gate(GT.AND_B, "X", A_N=self.arg1, B=self.arg2)
        elif self.truth_table == ((0, 1), (1, 0)):
            return np.create_gate(GT.XOR, "X", A=self.arg1, B=self.arg2)
        elif self.truth_table == ((0, 1), (1, 1)):
            return np.create_gate(GT.OR, "X", A=self.arg1, B=self.arg2)
        elif self.truth_table == ((1, 0), (0, 0)):
            return np.create_gate(GT.NOR, "Y", A=self.arg1, B=self.arg2)
        elif self.truth_table == ((1, 0), (0, 1)):
            return np.create_gate(GT.XNOR, "Y", A=self.arg1, B=self.arg2)
        elif self.truth_table == ((1, 0), (1, 1)):
            return np.create_gate(GT.OR_B, "X", A=self.arg1, B_N=self.arg2)
        elif self.truth_table == ((1, 1), (0, 1)):
            return np.create_gate(GT.OR_B, "X", A=self.arg2, B_N=self.arg1)
        elif self.truth_table == ((1, 1), (1, 0)):
            return np.create_gate(GT.NAND, "Y", A=self.arg1, B=self.arg2)
        else:
            raise ValueError(f"Invalid truth table in BinaryOp: {self.truth_table}")

    @classmethod
    def and_(cls, arg1, arg2):
        return cls(((0, 0), (0, 1)), arg1, arg2)

    @classmethod
    def nand(cls, arg1, arg2):
        return cls(((1, 1), (1, 0)), arg1, arg2)

    @classmethod
    def or_(cls, arg1, arg2):
        return cls(((0, 1), (1, 1)), arg1, arg2)

    @classmethod
    def nor(cls, arg1, arg2):
        return cls(((1, 0), (0, 0)), arg1, arg2)

    @classmethod
    def xor(cls, arg1, arg2):
        return cls(((0, 1), (1, 0)), arg1, arg2)

    @classmethod
    def xnor(cls, arg1, arg2):
        return cls(((1, 0), (0, 1)), arg1, arg2)

    @classmethod
    def less(cls, arg1, arg2):
        return cls(((0, 1), (0, 0)), arg1, arg2)

    @classmethod
    def less_or_equal(cls, arg1, arg2):
        return cls(((1, 1), (0, 1)), arg1, arg2)

    @classmethod
    def greater(cls, arg1, arg2):
        return cls(((0, 0), (1, 0)), arg1, arg2)

    @classmethod
    def greater_or_equal(cls, arg1, arg2):
        return cls(((1, 0), (1, 1)), arg1, arg2)

    @classmethod
    def symbolic(cls, op, arg1, arg2):
        if op == "&":
            return cls.and_(arg1, arg2)
        elif op == "~&":
            return cls.nand(arg1, arg2)
        elif op == "|":
            return cls.or_(arg1, arg2)
        elif op == "~|":
            return cls.nor(arg1, arg2)
        elif op == "^":
            return cls.xor(arg1, arg2)
        elif op == "~^" or op == "^~":
            return cls.xnor(arg1, arg2)
        elif op == "<":
            return cls.less(arg1, arg2)
        elif op == "<=":
            return cls.less_or_equal(arg1, arg2)
        elif op == ">":
            return cls.greater(arg1, arg2)
        elif op == ">=":
            return cls.greater_or_equal(arg1, arg2)
        else:
            raise SyntaxError(f"Unexpected binary bit operator: {op}")


class CompositeOp(BooleanOp):
    """boolean operator synthesizing to multiple gates"""

    def __init__(self, op, *args):
        self.op = op
        self.args = args

    def generate(self, np):
        arg_nodes = [a.generate(np) for a in self.args]
        op_inst = self.op(*arg_nodes)
        return op_inst.generate(np)


class MuxOp(BooleanOp):
    """single bit multiplexer operator with 3 inputs including the selector"""

    def __init__(self, selector, val0, val1):
        self.selector = selector
        self.val0 = val0
        self.val1 = val1

    def __new__(cls, selector, val0, val1):
        self = super().__new__(cls)
        assert_net_or_bit(selector, val0, val1)
        if isinstance(selector, BitNode):
            if selector.value == 0:
                return UnaryOp.buf(val0)
            elif selector.value == 1:
                return UnaryOp.buf(val1)
        elif isinstance(selector, DontCareNode):
            if isinstance(val0, DontCareNode) or isinstance(val1, DontCareNode):
                return BitConstant.dc
            elif isinstance(val0, BitNode):
                return BitConstant(val0)
            elif isinstance(val1, BitNode):
                return BitConstant(val1)
            else:
                return UnaryOp.buf(val0)
        assert isinstance(selector, NetNode)
        if isinstance(val0, BitNode):
            bit = val0.value
            return BinaryOp(((bit, bit), (0, 1)), selector, val1)
        elif isinstance(val0, DontCareNode):
            return UnaryOp.buf(val1)
        assert isinstance(val0, NetNode)
        if isinstance(val1, BitNode):
            bit = val1.value
            return BinaryOp(((0, 1), (bit, bit)), selector, val0)
        elif isinstance(val1, DontCareNode):
            return UnaryOp.buf(val0)
        assert isinstance(val1, NetNode)
        if config.split_mux:
            cond0 = BinaryOp(((0, 1), (0, 0)), self.selector, self.val0)
            cond1 = BinaryOp(((0, 0), (0, 1)), self.selector, self.val1)
            return CompositeOp(BinaryOp.or_, cond0, cond1)
        else:
            return self

    def generate(self, np):
        return np.create_gate(GT.MUX, "X", S=self.selector, A0=self.val0, A1=self.val1)


class GenericAdderOp(BooleanOp):
    """boolean operator with two output bits defined separately"""

    def __init__(self, cout_op, sum_op):
        self.cout = cout_op
        self.sum_ = sum_op

    def generate(self, np):
        return (self.cout.generate(np), self.sum_.generate(np))


class HalfAdderOp(BooleanOp):
    """boolean operator calculating bits of a+b for single bit a and b"""

    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __new__(cls, arg1, arg2):
        self = super().__new__(cls)
        assert_net_or_bit(arg1, arg2)
        if isinstance(arg1, DontCareNode) or isinstance(arg2, DontCareNode):
            cout = BitConstant.zero
            sum_ = BitConstant.dc
        elif (
            isinstance(arg1, BitNode)
            or isinstance(arg2, BitNode)
            or config.split_half_adder
        ):
            cout = BinaryOp.and_(arg1, arg2)
            sum_ = BinaryOp.xor(arg1, arg2)
            return GenericAdderOp(cout, sum_)
        else:
            return self

    def generate(self, np):
        return np.create_gate(GT.HA, ("COUT", "SUM"), A=self.arg1, B=self.arg2)


class HalfAdderPlusOneOp(BooleanOp):
    """boolean operator calculating bits of a+b+1 for single bit a and b"""

    def __new__(cls, arg1, arg2):
        super().__new__(cls)
        assert_net_or_bit(arg1, arg2)
        cout = BinaryOp.or_(arg1, arg2)
        sum_ = BinaryOp.xnor(arg1, arg2)
        return GenericAdderOp(cout, sum_)


class SplitFullAdderOp(BooleanOp):
    """version of the full adder implemented from two half adders"""

    def __init__(self, arg1, arg2, arg3):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def generate(self, np):
        cout1, sum1 = HalfAdderOp(self.arg1, self.arg2).generate(np)
        cout2, sum_ = HalfAdderOp(sum1, self.arg3).generate(np)
        cout = BinaryOp.or_(cout1, cout2).generate(np)
        return (cout, sum_)


class FullAdderOp(BooleanOp):
    """boolean operator calculcating a+b+c for single bit a, b and c"""

    def __init__(self, arg1, arg2, arg3):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def __new__(cls, arg1, arg2, arg3):
        self = super().__new__(cls)
        assert_net_or_bit(arg1, arg2, arg3)
        if isinstance(arg1, DontCareNode):
            cout = UnaryOp.buf(arg2)
            sum_ = BitConstant.dc
            return GenericAdderOp(cout, sum_)
        elif isinstance(arg2, DontCareNode) or isinstance(arg3, DontCareNode):
            cout = UnaryOp.buf(arg1)
            sum_ = BitConstant.dc
            return GenericAdderOp(cout, sum_)
        elif isinstance(arg1, BitNode) and arg1.value == 0:
            return HalfAdderOp(arg2, arg3)
        elif isinstance(arg2, BitNode) and arg2.value == 0:
            return HalfAdderOp(arg1, arg3)
        elif isinstance(arg3, BitNode) and arg3.value == 0:
            return HalfAdderOp(arg1, arg2)
        elif isinstance(arg1, BitNode) and arg1.value == 1:
            return HalfAdderPlusOneOp(arg2, arg3)
        elif isinstance(arg2, BitNode) and arg2.value == 1:
            return HalfAdderPlusOneOp(arg1, arg3)
        elif isinstance(arg3, BitNode) and arg3.value == 1:
            return HalfAdderPlusOneOp(arg1, arg2)
        elif config.split_full_adder:
            return SplitFullAdderOp(arg1, arg2, arg3)
        else:
            return self

    def generate(self, np):
        return self.create_gate(
            GT.FA, ("COUT", "SUM"), A=self.arg1, B=self.arg2, CIN=self.arg3
        )


# make most exports available under BooleanOp
BooleanOp.zero = BitConstant.zero
BooleanOp.one = BitConstant.one
BooleanOp.dc = BitConstant.dc
BooleanOp.buf = UnaryOp.buf
BooleanOp.inv = UnaryOp.inv
BooleanOp.and2 = BinaryOp.and_
BooleanOp.nand2 = BinaryOp.nand
BooleanOp.or2 = BinaryOp.or_
BooleanOp.nor2 = BinaryOp.nor
BooleanOp.xor2 = BinaryOp.xor
BooleanOp.xnor2 = BinaryOp.xnor
BooleanOp.less = BinaryOp.less
BooleanOp.less_or_equal = BinaryOp.less_or_equal
BooleanOp.greater = BinaryOp.greater
BooleanOp.greater_or_equal = BinaryOp.greater_or_equal
BooleanOp.symbolic_binary = BinaryOp.symbolic
BooleanOp.mux = MuxOp
BooleanOp.ha = HalfAdderOp
BooleanOp.hap = HalfAdderPlusOneOp
BooleanOp.fa = FullAdderOp
