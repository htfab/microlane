from ..util.logic import COMBINATIONAL_GATES, GT
from ..util.nodes import GateNode, ModuleNode, NetNode, NodeProcessor


class ClockSplitter(NodeProcessor):
    """synthesis step transforming flip flops to use two-phase nonoverlapping clocks
    in order to make the design more resistant to hold violations"""

    def __init__(self):
        pass

    def process_root(self, node):
        # props: modules
        self.config = node.config
        return self.pass_through(node)

    def process_module(self, node):
        # props: name, ports, symbols, nets, net_counter, inst_counter, gates, continuous_assignments, body
        split_clock = self.config["synth.split_clock"]
        if not split_clock:
            return node

        assert node.body is None
        self.nets = node.nets
        self.gates = []
        self.net_counter = node.net_counter
        self.inst_counter = 0

        # Find original clock and reset nets
        clock_net_name = self.config["synth.clock_net"]
        clock_nets = [n for n in self.nets if n.name == clock_net_name]
        if not clock_nets:
            raise RuntimeError(f'Clock net "{clock_net_name}" not found')
        if len(clock_nets) > 1:
            raise RuntimeError(f'Clock net "{clock_net_name}" ambiguous')
        clock_net = clock_nets[0]

        reset_n_net_name = self.config["synth.reset_n_net"]
        reset_n_nets = [n for n in self.nets if n.name == reset_n_net_name]
        if not reset_n_nets:
            raise RuntimeError(f'Negative reset net "{reset_n_net_name}" not found')
        if len(reset_n_nets) > 1:
            raise RuntimeError(f'Negative reset net "{reset_n_net_name}" ambiguous')
        reset_n_net = reset_n_nets[0]

        # Reserve nets for the two-phase nonoverlapping clock generator
        clock_gen_t1 = self.create_net()
        clock_gen_t2 = self.create_net()
        clock_gen_t3 = self.create_net()
        clock_gen_t4 = self.create_net()
        clock_gen_t5 = self.create_net()
        clock_gen_t6 = self.create_net()
        clock_phase1 = self.create_net()
        clock_phase2 = self.create_net()

        # Process existing gates, splitting flip-flops
        for gate in node.gates:
            assert isinstance(gate, GateNode)
            if gate.name in COMBINATIONAL_GATES:
                self.create_gate(gate.name, **gate.terminals)  # pass through
            elif gate.name == GT.DFF:
                # check flip-flop is valid and uses the expected original clock net
                dff_clk = gate.terminals["CLK"]
                dff_d = gate.terminals["D"]
                dff_q = gate.terminals["Q"]
                assert isinstance(dff_clk, NetNode)
                assert isinstance(dff_d, NetNode)
                assert isinstance(dff_q, NetNode)
                if dff_clk.name != clock_net.name:
                    raise RuntimeError(f"Unexpected clock net for flip-flop: {gate}")
                # split it into two latches driven by clock phase 1 & 2 respectively
                first_latch_q = self.create_gate(
                    GT.DLATCH, "Q", D=dff_d, GATE=clock_phase1
                )
                self.create_gate(GT.DLATCH, D=first_latch_q, GATE=clock_phase2, Q=dff_q)
            elif gate.name in (GT.DLATCH, GT.CLKGATE):
                raise RuntimeError(
                    f"Gate {gate.name} not supported in clock splitting step"
                )
            else:
                raise RuntimeError(
                    f"Unexpected gate {gate.name} in clock splitting step"
                )

        # Build the two-phase clock generator network
        self.create_gate(GT.INV, A=clock_net, Y=clock_gen_t1)
        self.create_gate(GT.DFF, CLK=clock_gen_t1, D=clock_gen_t6, Q=clock_gen_t2)
        self.create_gate(GT.INV, A=clock_gen_t2, Y=clock_gen_t3)
        self.create_gate(GT.DFF, CLK=clock_net, D=reset_n_net, Q=clock_gen_t4)
        self.create_gate(GT.OR_B, A=reset_n_net, B_N=clock_gen_t4, X=clock_gen_t5)
        self.create_gate(GT.AND_B, A_N=clock_gen_t2, B=clock_gen_t5, X=clock_gen_t6)
        self.create_gate(
            GT.CLKGATE, CLK=clock_net, GATE=clock_gen_t2, GCLK=clock_phase1
        )
        self.create_gate(
            GT.CLKGATE, CLK=clock_net, GATE=clock_gen_t3, GCLK=clock_phase2
        )

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
