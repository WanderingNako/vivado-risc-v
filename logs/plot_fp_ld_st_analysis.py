import glob
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline")
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp_ld_st_analysis.png")

# 事件编号: 11 -> fld, 12 -> fst
MEM_EVENTS = [11, 12]
OTHER_EVENTS = [4, 5, 6, 7, 8, 9, 10]


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
    mem_fracs = []

    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*"))):
        name = os.path.basename(path)
        header, events = parse_file(path)

        mem = sum(events.get(e, 0) for e in MEM_EVENTS)
        other = sum(events.get(e, 0) for e in OTHER_EVENTS)
        total = mem + other
        if total == 0:
            continue

        names.append(name)
        mem_fracs.append(mem / total)

    mem_fracs = np.array(mem_fracs, dtype=float)

    # 所有 benchmark 的平均访存占比（各 benchmark 等权算术平均）
    avg = mem_fracs.mean() if len(mem_fracs) else 0.0

    # 打印
    print(f"{'benchmark':<20}{'mem_frac':>12}")
    for name, frac in zip(names, mem_fracs):
        print(f"{name:<20}{frac:>12.4f}")
    print(f"{'Average':<20}{avg:>12.4f}")

    # 绘图：各 benchmark + 最后一根 Average
    labels = names + ["Average"]
    values = np.append(mem_fracs, avg)
    x = np.arange(len(labels))

    colors = ["tab:orange"] * len(names) + ["tab:red"]

    fig, ax = plt.subplots(figsize=(16, 9))
    bars = ax.bar(
        x,
        values,
        width=0.7,
        color=colors,
        edgecolor="white",
        linewidth=0.3,
    )

    # 每根柱子上标注数值
    for b, v in zip(bars, values):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + max(values) * 0.01,
            f"{v:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    # 平均线
    ax.axhline(avg, color="tab:red", linestyle="--", linewidth=1.5,
               label=f"Average = {avg:.3f}")

    ax.set_ylim(0, max(values) * 1.20 if len(values) else 1)
    ax.set_ylabel("Fraction of memory FP instructions (fld/fst)")
    ax.set_title("Committed FP memory instruction fraction (fld/fst) per benchmark")
    ax.set_xlabel("Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(loc="upper right", frameon=False)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved {OUT_PNG}")


if __name__ == "__main__":
    main()