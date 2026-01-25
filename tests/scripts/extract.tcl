gds read tt_um_microlane_demo.gds
select top cell
expand
extract path extfiles
extract all
ext2spice lvs
ext2spice short resistor
ext2spice -p extfiles
feedback save feedback.out
