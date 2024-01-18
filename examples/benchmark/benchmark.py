import os
import time
import siliconcompiler


# Setting up the experiment
def main():
    rootdir = os.path.dirname(__file__)
    parent = os.path.abspath(rootdir + "/..")

    examples = [{"heartbeat": 1000}, {"picorv32": 1000}, {"aes": 1500}]

    results = {}

    for item in examples:
        design = list(item.keys())[0]
        size = list(item.values())[0]

        rootdir = os.path.join(parent, design)
        results[design] = {}
        for n in [1, 2, 4, 8, 16]:
            wall_start = time.time()

            chip = siliconcompiler.Chip(design)
            chip.set("option", "jobname", f"job{n}")
            chip.set("option", "relax", True)
            chip.set("option", "quiet", True)
            chip.set("option", "remote", False)

            asic_flow_args = {"syn_np": n, "place_np": n, "cts_np": n, "route_np": n}
            chip.load_target("skywater130_demo", **asic_flow_args)

            # Set router to 1 thread to not interfere with measurement
            chip.set("tool", "openroad", "task", "route", "threads", 1)

            # load design
            if design == "picorv32":
                # picorv32 design is not shipped with sc, but can be automatically cloned from git
                chip.register_package_source(
                    name="picorv32",
                    path="git+https://github.com/YosysHQ/picorv32.git",
                    ref="c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42",
                )
                chip.input("picorv32.v", package="picorv32")
                chip.clock("clk", period=50)
            else:
                chip.input(f"{rootdir}/{design}.v")
                chip.input(f"{rootdir}/{design}.sdc")

            chip.set("constraint", "outline", [(0, 0), (size, size)])
            chip.set("constraint", "corearea", [(10, 10), (size - 10, size - 10)])

            # RUN
            chip.run()

            # OBSERVE/RECORD
            chip.summary()
            wall_end = time.time()
            walltime = round((wall_end - wall_start), 2)
            results[design][n] = walltime
            with open("results.txt", "a") as f:
                f.write(f"{design}, {n}, {walltime}\n")


if __name__ == "__main__":
    main()
