from ....util.tech_map import TechMap


class Sky130TechMap(TechMap):
    def buf_map(self, A, X):
        self.create_stdcell("sky130_fd_sc_hd__buf_1", A=A, X=X)

    def inv_map(self, A, Y):
        self.create_stdcell("sky130_fd_sc_hd__inv_1", A=A, Y=Y)

    def and2_map(self, A, B, X):
        self.create_stdcell("sky130_fd_sc_hd__and2_1", A=A, B=B, X=X)

    def and2b_map(self, A_N, B, X):
        self.create_stdcell("sky130_fd_sc_hd__and2b_1", A_N=A_N, B=B, X=X)

    def nand2_map(self, A, B, Y):
        self.create_stdcell("sky130_fd_sc_hd__nand2_1", A=A, B=B, Y=Y)

    def or2_map(self, A, B, X):
        self.create_stdcell("sky130_fd_sc_hd__or2_1", A=A, B=B, X=X)

    def or2b_map(self, A, B_N, X):
        self.create_stdcell("sky130_fd_sc_hd__or2b_1", A=A, B_N=B_N, X=X)

    def nor2_map(self, A, B, Y):
        self.create_stdcell("sky130_fd_sc_hd__nor2_1", A=A, B=B, Y=Y)

    def xor2_map(self, A, B, X):
        self.create_stdcell("sky130_fd_sc_hd__xor2_1", A=A, B=B, X=X)

    def xnor2_map(self, A, B, Y):
        self.create_stdcell("sky130_fd_sc_hd__xnor2_1", A=A, B=B, Y=Y)

    def mux_map(self, A0, A1, S, X):
        self.create_stdcell("sky130_fd_sc_hd__mux2_1", A0=A0, A1=A1, S=S, X=X)

    def ha_map(self, A, B, COUT, SUM):
        self.create_stdcell("sky130_fd_sc_hd__ha_1", A=A, B=B, COUT=COUT, SUM=SUM)

    def fa_map(self, A, B, CIN, COUT, SUM):
        self.create_stdcell(
            "sky130_fd_sc_hd__fa_1", A=A, B=B, CIN=CIN, COUT=COUT, SUM=SUM
        )

    def tielo_map(self, LO):
        self.create_stdcell("sky130_fd_sc_hd__conb_1", LO=LO)

    def tiehi_map(self, HI):
        self.create_stdcell("sky130_fd_sc_hd__conb_1", HI=HI)

    def dff_map(self, CLK, D, Q):
        self.create_stdcell("sky130_fd_sc_hd__dfxtp_1", CLK=CLK, D=D, Q=Q)

    def dlatch_map(self, D, GATE, Q):
        self.create_stdcell("sky130_fd_sc_hd__dlxtp_1", D=D, GATE=GATE, Q=Q)

    def clkgate_map(self, CLK, GATE, GCLK):
        self.create_stdcell("sky130_fd_sc_hd__dlclkp_1", CLK=CLK, GATE=GATE, GCLK=GCLK)


TECH_MAP = Sky130TechMap
