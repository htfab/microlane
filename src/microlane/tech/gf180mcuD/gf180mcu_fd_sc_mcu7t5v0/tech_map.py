from ....util.tech_map import TechMap


class Gf180McuTechMap(TechMap):
    def buf_map(self, A, X):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__buf_1", I=A, Z=X)

    def inv_map(self, A, Y):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__inv_1", I=A, ZN=Y)

    def and2_map(self, A, B, X):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__and2_1", A1=A, A2=B, Z=X)

    def and2b_map(self, A_N, B, X):
        t1 = self.create_net()
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__inv_1", I=A_N, ZN=t1)
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__and2_1", A1=t1, A2=B, Z=X)

    def nand2_map(self, A, B, Y):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__nand2_1", A1=A, A2=B, ZN=Y)

    def or2_map(self, A, B, X):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__or2_1", A1=A, A2=B, Z=X)

    def or2b_map(self, A, B_N, X):
        t1 = self.create_net()
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__inv_1", I=B_N, ZN=t1)
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__or2_1", A1=A, A2=t1, Z=X)

    def nor2_map(self, A, B, Y):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__nor2_1", A1=A, A2=B, ZN=Y)

    def xor2_map(self, A, B, X):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__xor2_1", A1=A, A2=B, Z=X)

    def xnor2_map(self, A, B, Y):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__xnor2_1", A1=A, A2=B, ZN=Y)

    def mux_map(self, A0, A1, S, X):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__mux2_1", I0=A0, I1=A1, S=S, Z=X)

    def ha_map(self, A, B, COUT, SUM):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__addh_1", A=A, B=B, CO=COUT, S=SUM)

    def fa_map(self, A, B, CIN, COUT, SUM):
        self.create_stdcell(
            "gf180mcu_fd_sc_mcu7t5v0__addf_1", A=A, B=B, CI=CIN, CO=COUT, S=SUM
        )

    def tielo_map(self, LO):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__tiel", ZN=LO)

    def tiehi_map(self, HI):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__tieh", Z=HI)

    def dff_map(self, CLK, D, Q):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__dffq_1", CLK=CLK, D=D, Q=Q)

    def dlatch_map(self, D, GATE, Q):
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__latq_1", D=D, E=GATE, Q=Q)

    def clkgate_map(self, CLK, GATE, GCLK):
        t1 = self.create_net()
        self.create_stdcell("gf180mcu_fd_sc_mcu7t5v0__tiel", ZN=t1)
        self.create_stdcell(
            "gf180mcu_fd_sc_mcu7t5v0__icgtp_1", CLK=CLK, E=GATE, TE=t1, Q=GCLK
        )


TECH_MAP = Gf180McuTechMap
