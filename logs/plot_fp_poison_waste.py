import glob
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FP_SPEC_DIR = os.path.join(BASE_DIR, "fp_spec_ld_wakeup")
OUT_PNG = os.path.join(BASE_DIR, "fp_poison_waste_rate.png")

EVENT_POISONED_ISS = 15
EVENT_POISON_KILL = 16


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


def main():
    names = []
    waste_rates = []
    iss_list = []
    kill_list = []

    for path in sorted(glob.glob(os.path.join(FP_SPEC_DIR, "*"))):
        name = os.path.basename(path)
        events = parse_file(path)
        iss = events.get(EVENT_POISONED_ISS, 0)
        kill = events.get(EVENT_POISON_KILL, 0)
        if iss == 0:
            continue
        waste_rate = kill / iss
        names.append(name)
        waste_rates.append(waste_rate)
        iss_list.append(iss)
        kill_list.append(kill)

    waste_rates = np.array(waste_rates)
    avg_rate = float(waste_rates.mean())

    print(f"{'benchmark':<20}{'iss':>12}{'kill':>12}{'waste rate':>14}")
    for name, iss, kill, rate in zip(names, iss_list, kill_list, waste_rates):
        print(f"{name:<20}{iss:>12}{kill:>12}{rate:>14.4f}")
    print(f"{'AVERAGE':<20}{'':>12}{'':>12}{avg_rate:>14.4f}")

    x = np.arange(len(names) + 1)
    bar_colors = ["skyblue"] * len(names) + ["orange"]
    bar_edges = ["steelblue"] * len(names) + ["darkorange"]
    all_rates = np.append(waste_rates, avg_rate)

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 6))
    ax.bar(x, all_rates, width=0.6, color=bar_colors, edgecolor=bar_edges)

    for xi, yi in zip(x, all_rates):
        ax.annotate(f"{yi * 100:.4f}%", (xi, yi), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8)

    ax.set_ylim(0, max(all_rates) * 1.2 if len(all_rates) > 0 else 1.0)
    ax.set_ylabel("FP poison waste rate")
    ax.set_title("FP poison waste rate per benchmark (fp_spec_ld_wakeup)")
    ax.set_xlabel("Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels(names + ["Average"], rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()