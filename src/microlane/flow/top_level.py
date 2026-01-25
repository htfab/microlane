from ..impl.floorplan import init_floorplan
from ..impl.patch import add_patch_metals
from ..impl.placement import run_placement
from ..impl.routing import run_routing
from ..impl.streamout import gds_streamout, lef_streamout
from ..synth.bit_blast import BitBlaster
from ..synth.clean import Cleaner
from ..synth.clock_split import ClockSplitter
from ..synth.elaborate import Elaborator
from ..synth.gl_export import get_netlist, write_gl_verilog
from ..synth.parse import parse, tokenize
from ..synth.tech_map import TechMapper
from ..tech import load_tech_data
from ..util import progress
from ..util.nodes import dump_tree
from .config import DEFAULT_CONFIG
from .report import write_metrics_json, write_pdk_json


class Flow:
    def __init__(self):
        self.config = dict(DEFAULT_CONFIG)

    def set_config(self, config):
        self.config.update(config)
        return self

    def load_tech(self):
        self.config["tech"] = load_tech_data(self.config["std_cell_library"])
        pdk_info = self.config["tech"]["pdk_info"]
        assert pdk_info["pdk"] == self.config["pdk"]
        assert pdk_info["pdk_variant"] == self.config["pdk_variant"]
        assert pdk_info["std_cell_library"] == self.config["std_cell_library"]

    def run(self):
        self.load_tech()
        config = self.config
        project_name = config["project_name"]
        run_dir = config["run_dir"]
        source_files = config["source_files"]
        show_progress = config["show_progress"]
        dump_synth_trees = config["debug.dump_synth_trees"]
        skip_routing = config["debug.skip_routing"]

        if len(source_files) != 1:
            raise NotImplementedError(
                "Only a single source file is supported at the moment"
            )
        source_file = source_files[0]

        progress.enable(show_progress)
        progress.step("Synthesis")
        source = open(source_file).read()

        progress.step("Parsing", 1)
        tree = parse(tokenize(source), config)
        if dump_synth_trees:
            with open(f"{run_dir}/s01_parse.tree", "w") as f:
                dump_tree(tree, f)

        progress.step("Bit blasting", 1)
        tree = BitBlaster().process(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s02_bit_blast.tree", "w") as f:
                dump_tree(tree, f)

        progress.step("Elaboration", 1)
        tree = Elaborator().process(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s03_elaborate.tree", "w") as f:
                dump_tree(tree, f)

        progress.step("Cleaning", 1)
        tree = Cleaner().process(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s04_clean.tree", "w") as f:
                dump_tree(tree, f)

        progress.step("Clock splitting", 1)
        tree = ClockSplitter().process(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s05_clock_split.tree", "w") as f:
                dump_tree(tree, f)

        progress.step("Tech mapping", 1)
        tree = TechMapper().process(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s06_tech_map.tree", "w") as f:
                dump_tree(tree, f)

        netlist = get_netlist(tree)
        if dump_synth_trees:
            with open(f"{run_dir}/s07_netlist.tree", "w") as f:
                dump_tree(netlist, f)

        if project_name is None:
            project_name = netlist.name

        progress.step("GL netlist export", 1)
        with open(f"{run_dir}/{project_name}.nl.v", "w") as f:
            write_gl_verilog(tree, f)

        with open(f"{run_dir}/{project_name}.pnl.v", "w") as f:
            write_gl_verilog(tree, f, powered=True)

        progress.step("Floorplanning")
        layout = init_floorplan(netlist)

        progress.step("Placement")
        run_placement(layout)

        if not skip_routing:
            progress.step("Routing")
            run_routing(layout)

            progress.step("Adding patch metals")
            add_patch_metals(layout)

        progress.step("Streamout")
        gds_streamout(layout, f"{run_dir}/{project_name}.gds")
        lef_streamout(layout, f"{run_dir}/{project_name}.lef")

        progress.step("Writing reports")
        write_pdk_json(layout, f"{run_dir}/{project_name}.pdk.json")
        write_metrics_json(layout, f"{run_dir}/{project_name}.metrics.json")

        progress.step("Finished")

        return layout
