import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter

log_dir = Path("logs/perf_analysis")
core = Path("generators/riscv-boom/src/main/scala/v3/exu/core.scala")
samples = {}
for path in sorted(log_dir.iterdir()):
    if not path.is_file():
        continue
    events = {}
    for line in path.read_text().splitlines():
        record = json.loads(line)
        match = re.fullmatch(r"event\s+(\d+)", record["type"])
        if match:
            event = int(match[1])
            assert event not in events and type(record["value"]) is int and record["value"] >= 0, path
            events[event] = record["value"]
        else:
            assert record["type"] == "max_inst", path
    assert set(events) == set(range(64)), path
    assert events[0] > 0 and events[1] > 0 and events[63] == 0, path
    for group in [(12, 13, 14), (15, 16, 17), (20, 21, 22), (27, 28, 29)]:
        assert sum(events[i] for i in group) == events[0], (path, group)
    assert events[3] <= events[2] and events[6] <= events[5], path
    assert events[30] <= events[26] and events[34] <= events[33], path
    samples[path.name] = events
assert len(samples) == 19

metrics = []
def ratio(title, numerator, denominator, unit="%", detail="", subtract=None):
    factor = {"%": 100, "per 1,000 retired instructions": 1000}.get(unit, 1)
    expression = f"E{numerator}" if subtract is None else f"(E{numerator} - E{subtract})"
    formula = f"{expression} / E{denominator}" + (f" × {factor:,}" if factor != 1 else "")
    values = [
        factor * (e[numerator] - (e[subtract] if subtract is not None else 0)) / e[denominator]
        if e[denominator] else math.nan
        for e in samples.values()
    ]
    assert all(math.isnan(value) or value >= 0 for value in values), title
    metrics.append((title, unit, formula, detail, values))

ratio("Instructions per cycle (IPC)", 1, 0, "instructions / cycle", "Architecturally retired instructions. The RTL delays the retirement increment by one cycle.")
ratio("I-cache miss rate", 2, 2, subtract=3, detail="Valid I-cache S2 accesses without a valid hit response. Replay attempts can be counted again.")
ratio("I-cache lower-level request ratio", 4, 2, detail="TileLink A-channel handshakes per valid I-cache S2 access.")
ratio("D-cache lower-level request ratio", 38, 36, detail="TileLink A-channel transaction completions per LSU-to-D-cache request lane accepted. Proxy for miss traffic.")
ratio("D-cache load/store NACK ratio", 37, 36, detail="Load/store NACKs per accepted request lane. NACK and tag miss are different events.")
ratio("ITLB miss rate", 5, 5, subtract=6, detail="Valid ITLB requests with the frontend miss flag. The flag excludes frontend replays.")
ratio("DTLB miss or backpressure rate", 34, 33, detail="Valid DTLB request lanes with response miss OR request not ready.")
ratio("ITLB page-walk request ratio", 7, 5, detail="PTW request handshakes per valid ITLB request.")
ratio("DTLB page-walk request ratio", 35, 33, detail="PTW request handshakes per valid DTLB request lane.")
for title, event in [("I-cache lower-level requests", 4), ("D-cache lower-level requests", 38), ("L2 TLB misses", 57)]:
    ratio(f"{title} per 1,000 instructions", event, 1, "per 1,000 retired instructions")

for stage, first, detail in [
    ("Fetch buffer", 12, "Zero uses packet valid. Full uses all lane valid bits. No handshake is required."),
    ("Decode", 15, "The classes are determined by decode lane fire signals."),
    ("Dispatch", 20, "The classes are determined by dispatch lane fire signals."),
    ("Integer and memory issue", 27, "The classes use integer and memory issue port valids before speculative wakeup cancellation."),
]:
    for offset, state in enumerate(("zero-output", "full-output", "partial-output")):
        ratio(f"{stage} {state} cycle share", first + offset, 0, detail=detail)

ratio("Integer and memory uops issued per cycle", 26, 0, "uops / cycle", "Counts issue port valids before speculative wakeup cancellation.")
ratio("Failed speculative wakeup share", 30, 26, detail="Issued uops with a poisoned operand when LSU signals a load miss.")
for title, event in [("Branch mask full", 18), ("ROB not ready for dispatch", 25), ("ROB rollback", 62)]:
    ratio(f"{title} cycle share", event, 0)
for title, event in [
    ("Rename stalls", 19), ("LDQ dispatch stalls", 23), ("STQ dispatch stalls", 24),
]:
    ratio(f"{title} per cycle", event, 0, "lanes / cycle", "The RTL sums lane flags each cycle, so the value can exceed one.")

for stage, base, misses in [("Execution", 39, 43), ("Retirement", 49, 53)]:
    for offset, kind in enumerate(("conditional branch", "JALR", "return-pattern JALR", "call-pattern JALR")):
        detail = (
            "Resolution-side b2 mispredict pulse divided by execution requests."
            if stage == "Execution" else
            "Retired matching uops marked debug_fsrc == BSRC_C divided by all retired matching uops."
        )
        ratio(f"{stage} {kind} misprediction ratio", misses + offset, base + offset, detail=detail)

for title, event in [("F1", 8), ("F2", 9), ("F3", 10), ("Core", 11)]:
    ratio(f"Next-PC source {title} events per cycle", event, 0, "events / cycle")

labels = {
    1: "Architecturally retired instructions",
    2: "Valid I-cache S2 accesses",
    3: "I-cache hit responses",
    4: "I-cache lower-level TileLink requests",
    5: "Valid ITLB requests",
    6: "Valid ITLB requests without frontend miss flag",
    7: "ITLB page-walk requests",
    12: "Fetch buffer zero-output cycles",
    13: "Fetch buffer full-output cycles",
    14: "Fetch buffer partial-output cycles",
    15: "Decode zero-output cycles",
    16: "Decode full-output cycles",
    17: "Decode partial-output cycles",
    19: "Rename stalled lane observations",
    20: "Dispatch zero-output cycles",
    21: "Dispatch full-output cycles",
    22: "Dispatch partial-output cycles",
    23: "LDQ dispatch stall lane observations",
    24: "STQ dispatch stall lane observations",
    25: "ROB not-ready cycles",
    26: "Integer and memory issued uops",
    27: "Integer and memory zero-issue cycles",
    28: "Integer and memory full-issue cycles",
    29: "Integer and memory partial-issue cycles",
    30: "Issued uops with failed speculative wakeup",
    33: "Valid DTLB request lanes",
    34: "DTLB miss or not-ready request lanes",
    35: "DTLB page-walk requests",
    36: "Accepted LSU-to-D-cache request lanes",
    37: "D-cache load/store NACKs",
    38: "D-cache lower-level TileLink A transaction completions",
    58: "Misaligned load/store exceptions",
    59: "Load/store page faults",
    60: "Fetch page faults",
    61: "Memory-ordering mini-exceptions",
    62: "ROB rollback cycles",
}
comments = {int(n): label.strip() for n, label in re.findall(
    r"event_counters\.io\.event_signals\((\d+)\) := [^\n]*?//([^\n]+)", core.read_text()
)}
assert set(comments) == set(range(63))
raw = [
    (f"E{i:02d}  {labels.get(i, comments[i])}", "raw count", f"E{i}",
     "Raw event total in the counter sampling window.", [e[i] for e in samples.values()])
    for i in range(63)
]

plt.rcParams.update({"pdf.fonttype": 42, "font.family": "DejaVu Sans", "axes.unicode_minus": False})
output = log_dir.parent / "boom_v3_benchmark_performance.pdf"

def sheet(pdf, heading, groups, page):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="#f8fafc")
    fig.text(.065, .925, heading, fontsize=24, weight="bold", color="#142642")
    y = .84
    for title, lines in groups:
        fig.text(.065, y, title, fontsize=13, weight="bold", color="#17496b")
        y -= .039
        for line in lines:
            fig.text(.065, y, line, fontsize=11, color="#253850")
            y -= .032
        y -= .026
    fig.text(.065, .053, f"BOOM v3  /  logs/logs  /  {page}", fontsize=9, color="#415570")
    pdf.savefig(fig)
    plt.close(fig)

def chart(pdf, metric, section, page):
    title, unit, formula, detail, values = metric
    fig, ax = plt.subplots(figsize=(11.7, 8.3), facecolor="#f8fafc")
    fig.subplots_adjust(left=.205, right=.91, bottom=.13, top=.82)
    fig.text(.065, .933, title, fontsize=21, weight="bold", color="#142642")
    fig.text(.065, .885, f"Formula  {formula}", fontsize=11, color="#17496b")
    if detail:
        fig.text(.065, .853, detail, fontsize=9.7, color="#415570")
    fig.text(.065, .045, f"{section}  /  logs/logs  /  {page}", fontsize=9, color="#415570")
    ax.set_facecolor("#f8fafc")
    ax.set_yticks(range(len(samples)), list(samples))
    ax.invert_yaxis()
    ax.tick_params(axis="both", color="#64748b", labelcolor="#253850")
    ax.set_xlabel(unit, labelpad=9)
    ax.grid(axis="x", alpha=.23)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    max_value = max((v for v in values if math.isfinite(v)), default=0)
    limit = max_value if max_value > 0 else 1
    ax.set_xlim(0, limit * 1.25)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.4g}"))
    for row, value in enumerate(values):
        if math.isnan(value):
            ax.text(limit * .015, row, "N/A", color="#59677c", fontsize=8, va="center")
        else:
            ax.barh(row, value, height=.63, color="#246e91", zorder=2)
            label = f"{int(value):,}" if unit == "raw count" else f"{value:.4g}"
            ax.text(value + limit * .015, row, label, fontsize=8, va="center", color="#253850")
    pdf.savefig(fig)
    plt.close(fig)

with PdfPages(output, metadata={"Title": "BOOM v3 benchmark performance counters"}) as pdf:
    sheet(pdf, "BOOM v3 benchmark performance", [
        ("Coverage", [f"{len(samples)} benchmarks from logs/logs. Each chart covers every benchmark in benchmark ID order.",
          f"Derived metrics on pages 3–{2 + len(metrics)}. Raw events E0–E62 on pages {3 + len(metrics)}–{2 + len(metrics) + len(raw)}.",
          "E63 has no assigned event and is zero in all logs. N/A indicates a zero denominator."]),
        ("Sampling and IPC", ["E<n> denotes the logged event counter. Each 64-bit counter adds its per-cycle increment.",
          "Counting requires the target process tag, an allowed privilege level and pfc_enable = 1.",
          "The counters reset on a committed counter-reset instruction or after warmup completes.",
          "The report uses the event-window counts. The separate max_inst record is excluded.",
          "IPC is E1 / E0, using the one-cycle-delayed architecturally valid retire count."]),
        ("Issue queue and execution units", ["Mean queue residency requires dispatch-to-issue timestamps or an occupancy integral",
          "with compatible departure accounting. These logs contain neither.",
          "E27 shows cycles with no integer or memory issue port valid. It measures issue starvation",
          "or other zero-issue conditions. Per-execution-unit idle cycles require per-unit busy signals.",
          "The issue signals omit the separate FP issue path. E26 counts pre-cancellation issue uops."]),
        ("Source", ["generators/riscv-boom/src/main/scala/v3/exu/core.scala and exu/event_counter.scala",
          "Cache and TLB signal definitions in ifu/icache.scala, ifu/frontend.scala, lsu/lsu.scala and lsu/dcache.scala"]),
    ], 1)
    sheet(pdf, "Cache, TLB and pipeline definitions", [
        ("Cache metrics", ["I-cache miss rate is (E2 - E3) / E2. Replayed S2 accesses can contribute to the counts.",
          "I-cache lower-level request ratio is E4 / E2. Misses can wait on an outstanding refill.",
          "D-cache lower-level request ratio is E38 / E36. E38 counts TileLink A transaction completions.",
          "E36 counts accepted request lanes, including retries if accepted again.",
          "D-cache NACK ratio is E37 / E36. NACKs can result from conflicts or resource backpressure.",
          "A true per-access D-cache miss rate requires a direct miss counter aligned with the request population."]),
        ("TLB metrics", ["ITLB miss rate is (E5 - E6) / E5, using the frontend miss flag that excludes replays.",
          "DTLB miss or backpressure rate is E34 / E33. E34 includes valid requests with ready low.",
          "E7 and E35 count PTW request handshakes. E57 is the PTW L2 TLB miss signal."]),
        ("Pipeline and branches", ["Zero, full and partial cycle shares use E0. Groups E12–E14, E15–E17, E20–E22 and E27–E29",
          "each sum to E0 in all 19 logs. Rename and queue stall counters can add multiple lanes per cycle.",
          "Branch ratios pair E43–E46 with E39–E42 at execution and E53–E56 with E49–E52 at retirement.",
          "Execution uses resolution-side mispredict pulses over execution requests. Retirement uses debug_fsrc.",
          "Returns and calls are JALR register-pattern subsets, so their counts overlap total JALR."]),
    ], 2)
    for page, metric in enumerate(metrics + raw, 3):
        chart(pdf, metric, "Derived metric" if page < 3 + len(metrics) else "Raw event", page)
    assert pdf.get_pagecount() == 2 + len(metrics) + len(raw)

print(f"{output}: {len(metrics)} derived charts, {len(raw)} raw event charts, 2 methodology pages")
