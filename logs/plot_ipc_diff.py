import glob
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASELINE_DIR = os.path.join(BASE_DIR, "baseline")
FP_SPEC_DIR = os.path.join(BASE_DIR, "none_recoded")
OUT_PNG = os.path.join(BASE_DIR, "ipc_diff_none_recoded.png")

EVENT_CYCLES = 0
EVENT_INSTS = 1


def parse_file(path):
    events = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            match = re.search(r"event\s+(\d+)", obj.get("type", ""))
            if match:
                events[int(match.group(1))] = obj["value"]
    return events


def compute_ipc(path):
    events = parse_file(path)
    cycles = events.get(EVENT_CYCLES, 0)
    insts = events.get(EVENT_INSTS, 0)
    if cycles == 0:
        return None
    return insts / cycles


def collect_ipcs(log_dir):
    result = {}
    for path in sorted(glob.glob(os.path.join(log_dir, "*"))):
        name = os.path.basename(path)
        ipc = compute_ipc(path)
        if ipc is not None:
            result[name] = ipc
    return result


def main():
    baseline = collect_ipcs(BASELINE_DIR)
    fp_spec = collect_ipcs(FP_SPEC_DIR)

    names = sorted(set(baseline.keys()) & set(fp_spec.keys()))
    if not names:
        print("No common benchmarks found.")
        return

    base_ipcs = np.array([baseline[name] for name in names])
    fp_ipcs = np.array([fp_spec[name] for name in names])
    diffs = fp_ipcs - base_ipcs
    rel_diffs = np.divide(
        diffs,
        base_ipcs,
        out=np.zeros_like(diffs),
        where=base_ipcs != 0,
    )

    print(f"{'benchmark':<20}{'baseline IPC':>14}{'fp_spec IPC':>14}{'diff':>12}{'rel diff':>12}")
    for name, b, f, d, r in zip(names, base_ipcs, fp_ipcs, diffs, rel_diffs):
        print(f"{name:<20}{b:>14.4f}{f:>14.4f}{d:>+12.4f}{r:>+12.2%}")

    avg_base = float(base_ipcs.mean())
    avg_fp = float(fp_ipcs.mean())
    avg_diff = avg_fp - avg_base
    avg_rel = avg_diff / avg_base if avg_base != 0 else 0.0
    print(f"{'AVERAGE':<20}{avg_base:>14.4f}{avg_fp:>14.4f}{avg_diff:>+12.4f}{avg_rel:>+12.2%}")

    x = np.arange(len(names))
    width = 0.38

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 6))
    bars1 = ax.bar(x - width / 2, base_ipcs, width, label="baseline",
                   color="skyblue", edgecolor="steelblue")
    bars2 = ax.bar(x + width / 2, fp_ipcs, width, label="fp_spec_ld_wakeup",
                   color="orange", edgecolor="darkorange")

    for bars in (bars1, bars2):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.4f}",
                        (bar.get_x() + bar.get_width() / 2, height),
                        textcoords="offset points",
                        xytext=(0, 4),
                        ha="center",
                        fontsize=8)

    for xi, rel in zip(x, rel_diffs):
        y = max(base_ipcs[xi], fp_ipcs[xi])
        ax.annotate(f"{rel:+.2%}",
                    (xi, y),
                    textcoords="offset points",
                    xytext=(0, 18),
                    ha="center",
                    fontsize=9,
                    color="red" if rel < 0 else "green")

    ax.set_ylabel("IPC")
    ax.set_title("IPC comparison: baseline vs fp_spec_ld_wakeup")
    ax.set_xlabel("Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()