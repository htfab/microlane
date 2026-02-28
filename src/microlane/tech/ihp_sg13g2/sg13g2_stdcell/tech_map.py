from ....util.tech_map import TechMap


class IhpTechMap(TechMap):
    def buf_map(self, A, X):
        self.create_stdcell("sg13g2_buf_1", A=A, X=X)

    def inv_map(self, A, Y):
        self.create_stdcell("sg13g2_inv_1", A=A, Y=Y)

    def and2_map(self, A, B, X):
        self.create_stdcell("sg13g2_and2_1", A=A, B=B, X=X)

    def and2b_map(self, A_N, B, X):
        self.create_stdcell("sg13g2_nor2b_1", A=A_N, B_N=B, Y=X)

    def nand2_map(self, A, B, Y):
        self.create_stdcell("sg13g2_nand2_1", A=A, B=B, Y=Y)

    def or2_map(self, A, B, X):
        self.create_stdcell("sg13g2_or2_1", A=A, B=B, X=X)

    def or2b_map(self, A, B_N, X):
        self.create_stdcell("sg13g2_nand2b_1", A_N=A, B=B_N, Y=X)

    def nor2_map(self, A, B, Y):
        self.create_stdcell("sg13g2_nor2_1", A=A, B=B, Y=Y)

    def xor2_map(self, A, B, X):
        self.create_stdcell("sg13g2_xor2_1", A=A, B=B, X=X)

    def xnor2_map(self, A, B, Y):
        self.create_stdcell("sg13g2_xnor2_1", A=A, B=B, Y=Y)

    def mux_map(self, A0, A1, S, X):
        self.create_stdcell("sg13g2_mux2_1", A0=A0, A1=A1, S=S, X=X)

    def ha_map(self, A, B, COUT, SUM):
        self.create_stdcell("sg13g2_and2_1", A=A, B=B, X=COUT)
        self.create_stdcell("sg13g2_xor2_1", A=A, B=B, X=SUM)

    def fa_map(self, A, B, CIN, COUT, SUM):
        t1 = self.create_net()
        t2 = self.create_net()
        t3 = self.create_net()
        self.ha_map(A=A, B=B, COUT=t1, SUM=t2)
        self.ha_map(A=CIN, B=t2, COUT=t3, SUM=SUM)
        self.create_stdcell("sg13g2_or2_1", A=t1, B=t3, X=COUT)

    def tielo_map(self, LO):
        self.create_stdcell("sg13g2_tielo", L_LO=LO)

    def tiehi_map(self, HI):
        self.create_stdcell("sg13g2_tiehi", L_HI=HI)

    def dff_map(self, CLK, D, Q):
        t1 = self.create_net()
        self.create_stdcell("sg13g2_tiehi", L_HI=t1)
        self.create_stdcell("sg13g2_dfrbpq_1", CLK=CLK, D=D, RESET_B=t1, Q=Q)

    def dlatch_map(self, D, GATE, Q):
        self.create_stdcell("sg13g2_dlhq_1", D=D, GATE=GATE, Q=Q)

    def clkgate_map(self, CLK, GATE, GCLK):
        self.create_stdcell("sg13g2_lgcp_1", CLK=CLK, GATE=GATE, GCLK=GCLK)


TECH_MAP = IhpTechMap
