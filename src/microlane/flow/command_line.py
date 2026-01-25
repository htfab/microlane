import os
import sys

from .top_level import Flow


def main():
    # we were launched using "python -m ..." or the script defined in pyproject.toml?
    is_module = sys.argv[0].endswith("__main__.py")
    module_name = __package__.split(".")[0]
    # make sure we are deterministic
    if "PYTHONHASHSEED" not in os.environ:
        os.environ["PYTHONHASHSEED"] = "0"
        # relaunch python so that PYTHONHASHSEED takes effect
        if is_module:
            new_argv = [sys.executable, "-m", module_name, *sys.argv[1:]]
        else:
            new_argv = [sys.executable, *sys.argv]
        os.execv(sys.executable, new_argv)

    # check that we have an input file specified
    if len(sys.argv) != 2:
        if is_module:
            command = os.path.basename(sys.executable)
            print(f"Usage: {command} -m {module_name} <project.v>", file=sys.stderr)
        else:
            command = os.path.basename(sys.argv[0])
            print(f"Usage: {command} <project.v>", file=sys.stderr)
        exit(1)
    source_file = sys.argv[1]

    flow = Flow()
    flow.config.update(
        {
            "source_files": (source_file,),
            "run_dir": ".",
        }
    )
    flow.run()
