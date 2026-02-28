class TechMap:
    def __init__(self, node_processor):
        self.node_processor = node_processor

    def map_gate(self, name, terminals):
        map_dict = {
            "BUF": self.buf_map,
            "INV": self.inv_map,
            "AND": self.and2_map,
            "AND_B": self.and2b_map,
            "NAND": self.nand2_map,
            "OR": self.or2_map,
            "OR_B": self.or2b_map,
            "NOR": self.nor2_map,
            "XOR": self.xor2_map,
            "XNOR": self.xnor2_map,
            "MUX": self.mux_map,
            "HA": self.ha_map,
            "FA": self.fa_map,
            "TIELO": self.tielo_map,
            "TIEHI": self.tiehi_map,
            "DFF": self.dff_map,
            "DLATCH": self.dlatch_map,
            "CLKGATE": self.clkgate_map,
        }
        try:
            map_func = map_dict[name]
        except KeyError:
            raise RuntimeError(f"No tech map found for gate {name}")
        return map_func(**terminals)

    def create_net(self):
        return self.node_processor.create_net()

    def create_stdcell(self, name, **terminals):
        return self.node_processor.create_gate(name, **terminals)

    def buf_map(A, X):
        raise NotImplementedError

    def inv_map(A, Y):
        raise NotImplementedError

    def and2_map(A, B, X):
        raise NotImplementedError

    def and2b_map(A_N, B, X):
        raise NotImplementedError

    def nand2_map(A, B, Y):
        raise NotImplementedError

    def or2_map(A, B, X):
        raise NotImplementedError

    def or2b_map(A, B_N, X):
        raise NotImplementedError

    def nor2_map(A, B, Y):
        raise NotImplementedError

    def xor2_map(A, B, X):
        raise NotImplementedError

    def xnor2_map(A, B, Y):
        raise NotImplementedError

    def mux_map(A0, A1, S, X):
        raise NotImplementedError

    def ha_map(A, B, COUT, SUM):
        raise NotImplementedError

    def fa_map(A, B, CIN, COUT, SUM):
        raise NotImplementedError

    def tielo_map(LO):
        raise NotImplementedError

    def tiehi_map(HI):
        raise NotImplementedError

    def dff_map(CLK, D, Q):
        raise NotImplementedError

    def dlatch_map(D, GATE, Q):
        raise NotImplementedError

    def clkgate_map(CLK, GATE, GCLK):
        raise NotImplementedError
