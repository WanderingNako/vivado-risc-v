import glob
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp_analysis.png")

FP_LABELS = ["fmul", "fadd", "fma", "f2i", "f2f", "fdiv", "fsqrt", "fld", "fst"]
FP_EVENTS = list(range(4, 13))


def parse_file(path):
    header = {}
    events = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("type") == "max_inst":
                header = obj
                continue
            match = re.search(r"event\s+(\d+)", obj.get("type", ""))
            if match:
                events[int(match.group(1))] = obj["value"]
    return header, events


def main():
    names = []
    fp_counts = []
    ipc_values = []

    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*"))):
        name = os.path.basename(path)
        header, events = parse_file(path)
        fp = [events.get(e, 0) for e in FP_EVENTS]
        if sum(fp) == 0:
            continue
        e0 = events.get(0, 0)
        e1 = events.get(1, 0)
        ipc = e1 / e0 if e0 else 0.0
        names.append(name)
        fp_counts.append(fp)
        ipc_values.append(ipc)

    fp_counts = np.array(fp_counts, dtype=float)
    fractions = fp_counts / fp_counts.sum(axis=1, keepdims=True)
    ipc_values = np.array(ipc_values)

    print(f"{'benchmark':<20}{'IPC(e1/e0)':>12}  " + "".join(f"{l:>10}" for l in FP_LABELS))
    for name, ipc, counts in zip(names, ipc_values, fp_counts):
        print(f"{name:<20}{ipc:>12.4f}  " + "".join(f"{int(c):>10}" for c in counts))

    x = np.arange(len(names))
    fig, ax_bar = plt.subplots(figsize=(16, 9))

    cmap = plt.get_cmap("tab10")
    bottom = np.zeros(len(names))
    for i, label in enumerate(FP_LABELS):
        ax_bar.bar(
            x,
            fractions[:, i],
            bottom=bottom,
            width=0.7,
            color=cmap(i % 10),
            label=label,
            edgecolor="white",
            linewidth=0.3,
        )
        bottom += fractions[:, i]

    ax_bar.set_ylim(0, 1)
    ax_bar.set_ylabel("Fraction of FP instructions")
    ax_bar.set_title("Committed FP instruction mix and IPC")
    ax_bar.set_xlabel("Benchmark")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(names, rotation=45, ha="right")
    ax_bar.legend(ncol=9, loc="upper center", bbox_to_anchor=(0.5, 1.10), frameon=False)

    ax_ipc = ax_bar.twinx()
    ax_ipc.plot(x, ipc_values, color="skyblue", linestyle="--", linewidth=3.0,
                marker="o", markersize=6, label="IPC")
    ax_ipc.set_ylabel("IPC")
    ax_ipc.set_ylim(0, max(ipc_values) * 1.25)
    ax_ipc.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()
