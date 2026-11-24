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
OUT_PNG = os.path.join(BASE_DIR, "fp_wakeup_accuracy.png")

EVENT_WAKEUP_TOTAL = 13
EVENT_WAKEUP_MISS = 14


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
    accuracies = []
    totals = []
    misses = []

    for path in sorted(glob.glob(os.path.join(FP_SPEC_DIR, "*"))):
        name = os.path.basename(path)
        events = parse_file(path)
        total = events.get(EVENT_WAKEUP_TOTAL, 0)
        miss = events.get(EVENT_WAKEUP_MISS, 0)
        if total == 0:
            continue
        accuracy = (total - miss) / total
        names.append(name)
        accuracies.append(accuracy)
        totals.append(total)
        misses.append(miss)

    accuracies = np.array(accuracies)
    avg_accuracy = float(accuracies.mean())

    print(f"{'benchmark':<20}{'total':>12}{'miss':>12}{'accuracy':>14}")
    for name, total, miss, acc in zip(names, totals, misses, accuracies):
        print(f"{name:<20}{total:>12}{miss:>12}{acc:>14.4f}")
    print(f"{'AVERAGE':<20}{'':>12}{'':>12}{avg_accuracy:>14.4f}")

    x = np.arange(len(names) + 1)
    bar_colors = ["skyblue"] * len(names) + ["orange"]
    bar_edges = ["steelblue"] * len(names) + ["darkorange"]
    all_accs = np.append(accuracies, avg_accuracy)

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 6))
    ax.bar(x, all_accs, width=0.6, color=bar_colors, edgecolor=bar_edges)

    for xi, yi in zip(x, all_accs):
        ax.annotate(f"{yi * 100:.4f}%", (xi, yi), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8)

    ax.set_ylim(0, 1.1)
    ax.set_ylabel("FP wakeup accuracy")
    ax.set_title("FP wakeup accuracy per benchmark (fp_spec_ld_wakeup)")
    ax.set_xlabel("Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels(names + ["Average"], rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()