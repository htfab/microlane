from .._version import __version__


def write_pdk_json(layout, filename):
    flow_name = __package__.split(".")[0]
    flow_version = __version__
    pdk_info = layout.config["tech"]["pdk_info"]
    pdk_variant = pdk_info["pdk_variant"]
    pdk_source = pdk_info["pdk_source"]
    pdk_version = pdk_info["pdk_version"]
    with open(filename, "w") as f:
        f.write("{\n")
        f.write(f'  "FLOW_NAME": "{flow_name}",\n')
        f.write(f'  "FLOW_VERSION": "{flow_version}",\n')
        f.write(f'  "PDK": "{pdk_variant}",\n')
        f.write(f'  "PDK_SOURCE": "{pdk_source}",\n')
        f.write(f'  "PDK_VERSION": "{pdk_version}"\n')
        f.write("}\n")


def write_metrics_json(layout, filename):
    utilization = layout.metrics.get("utilization", 0)
    wire_length = layout.metrics.get("wire_length", 0)
    wire_length = round(wire_length / 1000)
    with open(filename, "w") as f:
        f.write("{\n")
        f.write(f'  "utilization": {utilization:.7f},\n')
        f.write(f'  "wire_length": {wire_length}\n')
        f.write("}\n")
