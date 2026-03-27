# microlane

## Self-contained RTL to GDS flow for simple chip designs

In a quest to better understand the chip hardening flow I challenged myself to
write minimal implementations of Verilog parsing, synthesis, floorplanning,
placement, routing and GDS streamout such that they can transform a simple RTL
design into a layout that can be manufactured on Tiny Tapeout.

Of course, many corners were cut. 7000 lines of Python code written over a
couple of weeks won't stand up to any serious EDA tool. But it does harden the
demo design in a way that it passes DRC, LVS and the Tiny Tapeout precheck, as
well as the gate-level cocotb testbench and the transistor-level SPICE
simulation.

### Limitations

- Only the sky130, ihp-sg13g2 & ihp-sg13cmos5l PDKs are supported.
- The floorplan is fixed to use a single 1x1 Tiny Tapeout tile.
- The design has to fit in a single Verilog module.
- There is only one clock domain. All synchronous logic has to use `posedge clk`.
- The gate level netlist is not optimised, so the area needed will be higher than usual.
- There is no static timing analysis. To prevent hold violations the design is
  modified to use a two phase non-overlapping clock generated internally.
  This ensures that it will work at some frequency but not at a particular one
  known in advance. Also, two physical clock ticks will correspond to one
  logical clock tick.
- There is no separate global and detailed placement, nor global and detailed
  routing. Performing them in a single step incurs extra runtime and memory use.
- There is no antenna check.
- The flow is in general rough around the edges. Features not covered by the demo
  design are only lightly tested and might break or raise "not implemented" errors.
  Changing the random seed can cause DRC violations in designs that worked previously.
- DRC, LVS, etc. are not part of the flow. You will need external tools for
  verification.

### Usage

You can try hardening the [demo design](tests/src/demo.v) with:
```
pip install microlane
export PDK=sky130A
microlane demo.v
```

The command line interface writes outputs to the current directory and uses
fixed settings. For more control, you can import the microlane library from a
[script](tests/scripts/harden.py) and change the
[configuration](src/microlane/flow/config.py).

### References

These resources have been helpful in designing the microlane flow:
- [VLSI CAD course](
    https://archive.org/details/academictorrents_625ae5f99f1cfdc2b8eb42577ca5271ad78967e0)
    by Rob A. Rutenbar
- [Digital VLSI Design course](
    https://www.youtube.com/playlist?list=PLZU5hLL_713x0_AV_rVbay0pWmED7992G)
    by Adi Teman
- [Slides for the VLSI Physical Design book](
    https://www.ifte.de/books/eda/index.html)
    by Andrew B. Kahng et al.
- [Yosys internals](
    https://yosyshq.readthedocs.io/projects/yosys/en/latest/yosys_internals/index.html)
    documentation page
- [TritonRoute article](
    https://vlsicad.ucsd.edu/Publications/Journals/j133.pdf)
    by Andrew B. Kahng et al.
- [Tutorial series on writing a parser](
    https://www.youtube.com/playlist?list=PLZQftyCk7_SdoVexSmwy_tBgs7P0b97yD)
    by CodePulse
