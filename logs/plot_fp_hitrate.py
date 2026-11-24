import glob
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp_hitrate.png")

FP_ACCESS = 2
FP_HIT = 3


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
    hit_rates = []

    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*"))):
        name = os.path.basename(path)
        events = parse_file(path)
        access = events.get(FP_ACCESS, 0)
        hit = events.get(FP_HIT, 0)
        if access == 0:
            continue
        names.append(name)
        hit_rates.append(hit / access)

    hit_rates = np.array(hit_rates)
    avg_rate = float(hit_rates.mean())

    print(f"{'benchmark':<20}{'FP D$ hit rate':>16}")
    for name, rate in zip(names, hit_rates):
        print(f"{name:<20}{rate:>16.4f}")
    print(f"{'AVERAGE':<20}{avg_rate:>16.4f}")

    x = np.arange(len(names) + 1)
    bar_colors = ["skyblue"] * len(names) + ["orange"]
    bar_edges = ["steelblue"] * len(names) + ["darkorange"]
    all_rates = np.append(hit_rates, avg_rate)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, all_rates, width=0.6, color=bar_colors, edgecolor=bar_edges)
    for xi, yi in zip(x, all_rates):
        ax.annotate(f"{yi * 100:.1f}%", (xi, yi), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=9)

    ax.set_ylim(0, 1.1)
    ax.set_ylabel("FP load D$ hit rate")
    ax.set_title("FP load D$ hit rate per benchmark")
    ax.set_xlabel("Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels(names + ["Average"], rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()
