gds read tt_um_microlane_demo.gds
select top cell
expand
drc style drc(full)
drc check
drc catchup
puts stdout [drc listall why]
