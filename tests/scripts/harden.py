#!/usr/bin/env python3

import os

import microlane

microlane.Flow(os.environ["PDK"]).set_config(
    {"source_files": [f"{os.environ['TEST_ROOT']}/src/demo.v"]}
).run()
