import sst
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--num_chiplets", type=int, default=1)
parser.add_argument("--trace_dir",    type=str, required=True)
parser.add_argument("--vec_depth",    type=int, default=64)
parser.add_argument("--clock",        type=str, default="1GHz")
parser.add_argument("--link_bw",      type=str, default="100GB/s")
parser.add_argument("--hops",         type=int, default=2)
parser.add_argument("--num_add",      type=int, default=4)
parser.add_argument("--num_mul",      type=int, default=4)
parser.add_argument("--num_ntt",      type=int, default=2)
parser.add_argument("--num_rot",      type=int, default=1)
parser.add_argument("--num_tra",      type=int, default=2)
parser.add_argument("--num_bcu",      type=int, default=2)
parser.add_argument("--num_evg",      type=int, default=1)
parser.add_argument("--mem_bw",       type=str, default="200GB/s")
parser.add_argument("--mem_latency",  type=str, default="100ns")
args, _ = parser.parse_known_args()

num_chiplets = args.num_chiplets

cpu = sst.Component("cpu", "cinnamon.CPU")
cpu.addParams({
    "clock":        args.clock,
    "num_chiplets": num_chiplets,
    "vec_depth":    args.vec_depth,
    "verbose":      0,
})

network = cpu.setSubComponent("network", "cinnamon.CinnamonNetwork")
network.addParams({
    "verbose": 0,
    "hops":    args.hops,
    "linkBW":  args.link_bw,
})

for i in range(num_chiplets):
    chiplet = cpu.setSubComponent("chiplet_{}".format(i), "cinnamon.CinnamonChiplet")
    chiplet.addParams({
        "verbose":            0,
        "numVectorRegs":      1024,
        "numAddUnits":        args.num_add,
        "numMulUnits":        args.num_mul,
        "numNttUnits":        args.num_ntt,
        "numRotUnits":        args.num_rot,
        "numTraUnits":        args.num_tra,
        "numBcuUnits":        args.num_bcu,
        "numBcuBuffs":        args.num_bcu,
        "numEvgUnits":        args.num_evg,
        "usePRNG":            True,
        "memoryRequestWidth": 1024,
    })

    reader = chiplet.setSubComponent("reader", "cinnamon.CinnamonTextTraceReader")
    trace_file = os.path.join(args.trace_dir, "chiplet_{}.trace".format(i))
    reader.addParams({"file": trace_file})

    memory = chiplet.setSubComponent("memory", "memHierarchy.standardInterface")
    memory.addParams({"verbose": 0})

    memctrl = sst.Component("memctrl_{}".format(i), "memHierarchy.MemController")
    memctrl.addParams({
        "clock":          args.clock,
        "addr_range_end": 1024 * 1024 * 1024 - 1,
        "verbose":        0,
    })

    membk = memctrl.setSubComponent("backend", "memHierarchy.simpleDRAM")
    membk.addParams({
        "max_requests_per_cycle": -1,
        "mem_size":               "1GiB",
        "tCAS":                   2,
        "tRCD":                   2,
        "tRP":                    3,
        "cycle_time":             args.mem_latency,
        "row_size":               "8KiB",
        "row_policy":             "open",
    })

    link = sst.Link("mem_link_{}".format(i))
    link.connect(
        (memory,  "port",        "1ns"),
        (memctrl, "direct_link", "1ns"),
    )
