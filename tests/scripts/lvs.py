#!/usr/bin/env python3

import os

layout_spice = "tt_um_microlane_demo.spice"
gl_netlist = "gate_level_netlist.v"

pdk = os.environ["PDK"]

if pdk == "sky130A":
    power_map = {
        "VPWR": "VPWR",
        "VGND": "VGND",
        "VPB": "VPWR",
        "VNB": "VGND",
    }
    stdcell_prefix = "sky130_fd_sc_hd__"
elif pdk == "ihp-sg13g2":
    power_map = {
        "VDD": "VPWR",
        "VSS": "VGND",
    }
    stdcell_prefix = "sg13g2_"
else:
    raise NotImplementedError("Unknown PDK")


layout_instances = {}
with open(layout_spice) as f:
    contents = f.read().replace("\n+", "")
    lines = contents.strip().split("\n")
    top_level = False
    pins = {}
    for line in lines:
        ld = line.strip().split()
        if not ld:
            continue
        elif ld[0] == ".subckt":
            pins[ld[1]] = ld[2:]
            top_level = ld[1].startswith("tt_um_")
        elif ld[0] == ".ends":
            top_level = False
        elif top_level:
            if ld[0].startswith("R"):
                print(f"Warning: resistor in SPICE file: {line.strip()}")
                continue
            assert ld[0].startswith("X")
            inst = ld[0][1:]
            cell = ld[-1]
            assert cell in pins
            connections = ld[1:-1]
            assert len(connections) == len(pins[cell])
            conn_dict = dict(zip(pins[cell], connections))
            for k, v in power_map.items():
                assert conn_dict[k] == v
                del conn_dict[k]
            if not conn_dict:
                continue
            assert inst not in layout_instances
            layout_instances[inst] = conn_dict

gl_instances = {}
with open(gl_netlist) as f:
    contents = f.read()
    lines = contents.strip().replace("\n", "").split(";")
    for line in lines:
        ld = line.strip().split(")")
        if not ld[0].startswith(stdcell_prefix):
            continue
        ls = ld[0].split()
        cell = ls[0]
        inst = ls[1]
        conn_dict = {}
        for la in ld:
            if "." in la:
                la = la.split(".")[1]
                key, value = la.split("(")
                assert key not in conn_dict
                conn_dict[key] = value
        for k, v in power_map.items():
            assert conn_dict[k] == v
            del conn_dict[k]
        assert inst not in gl_instances
        gl_instances[inst] = conn_dict

gl_match = {}
layout_match = {}
assert sorted(layout_instances.keys()) == sorted(gl_instances.keys())
for inst in layout_instances.keys():
    layout_inst = layout_instances[inst]
    gl_inst = gl_instances[inst]
    for pin in gl_inst:
        assert pin in layout_inst
    for pin in layout_inst:
        if pin not in gl_inst:
            gl_inst[pin] = f"unique_{inst}_{pin}"
        layout_net = layout_inst[pin]
        gl_net = gl_inst[pin]
        if layout_net not in layout_match:
            layout_match[layout_net] = (inst, pin)
            assert gl_net not in gl_match
            gl_match[gl_net] = (inst, pin)
        elif gl_net in gl_match:
            assert layout_net in layout_match
            assert layout_match[layout_net] == gl_match[gl_net]
        else:
            prev = "/".join(layout_match[layout_net])
            current = "/".join((inst, pin))
            print(f"short: {prev}, {current}")
