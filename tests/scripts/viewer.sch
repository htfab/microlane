v {xschem version=3.4.8RC file_version=1.2}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 20 -450 820 -50 {flags=graph
y1=-0.00076
y2=1.9
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=1.5625e-10
x2=0.001
divx=5
subdivx=1
xlabmag=1.0
ylabmag=1.0
node="clk
rst_n
uo_out[0]
uo_out[1]
uo_out[2]
uo_out[3]
uo_out[4]
uo_out[5]
uo_out[6]
uo_out[7]"
color="4 5 6 7 8 9 10 12 13 14"
dataset=-1
unitx=1
logx=0
logy=0
}
C {launcher.sym} 690 -30 0 0 {name=h5
descr="load waves" 
tclcommand="xschem raw_read sim.raw tran"
}
