"""
Gera 6 gráficos de alta resolução (300 DPI) a partir dos resultados reais
salvos em /app/results/benchmark_results.json.
"""

import json
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_PATH = Path("/app/results/benchmark_results.json")
STRESS_PATH = Path("/app/results/stress_results.json")
CHARTS_DIR = Path("/app/results/charts")

PROTOCOLS = ["SOAP", "REST", "GraphQL", "gRPC"]
LANGUAGES = ["Python", "Node.js (TS)"]

COLORS = {
    "SOAP": "#D97706",     # Âmbar
    "REST": "#2563EB",     # Azul
    "GraphQL": "#DB2777",  # Magenta
    "gRPC": "#0F766E",     # Teal
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.7,
    "figure.facecolor": "white",
    "axes.facecolor": "#F8FAFC",
})


def load_results() -> List[Dict]:
    with RESULTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)["results"]


def index_results(rows: List[Dict]) -> Dict:
    idx = {}
    for r in rows:
        idx[(r["language"], r["protocol"], r["workload"], r["concurrency"])] = r
    return idx


def add_bar_labels(ax, rects, fmt="{:.1f}", fontsize=8.5, offset=3, auto_compact=False):
    for rect in rects:
        h = rect.get_height()
        txt = f"{h:.0f}" if (auto_compact and h >= 100) else fmt.format(h)
        ax.annotate(
            txt,
            xy=(rect.get_x() + rect.get_width() / 2, h),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
            fontweight="bold",
            color="#1E293B",
        )


def chart_01_p95_by_concurrency(idx: Dict):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
    concurrencies = [10, 50, 100]
    labels = ["Leve (10 VUs)", "Moderada (50 VUs)", "Alta (100 VUs)"]
    x = np.arange(len(concurrencies))
    width = 0.19

    for ax, lang in zip(axes, LANGUAGES):
        for i, proto in enumerate(PROTOCOLS):
            vals = [idx[(lang, proto, "W1_list_songs", c)]["p95_ms"] for c in concurrencies]
            rects = ax.bar(x + (i - 1.5) * width, vals, width, label=proto, color=COLORS[proto], zorder=3)
            add_bar_labels(ax, rects, fmt="{:.1f}", fontsize=8, auto_compact=True)
        ax.set_title(f"{lang}", fontsize=13, fontweight="bold", color="#0F172A", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.grid(axis="y", zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylim(0, axes[0].get_ylim()[1] * 1.12)

    axes[0].set_ylabel("Latência p95 (ms) — menor é melhor", fontsize=11, fontweight="bold", color="#334155")
    handles, leg_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, leg_labels, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, frameon=False, fontsize=11)
    fig.suptitle("Latência p95 sob Diferentes Níveis de Carga (W1: Listagem de 100 Músicas)", fontsize=14, fontweight="bold", color="#0F172A", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(CHARTS_DIR / "01_p95_latency_by_concurrency.png", dpi=300)
    plt.close(fig)


def chart_02_throughput_by_concurrency(idx: Dict):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
    concurrencies = [10, 50, 100]
    labels = ["Leve (10 VUs)", "Moderada (50 VUs)", "Alta (100 VUs)"]
    x = np.arange(len(concurrencies))
    width = 0.19

    for ax, lang in zip(axes, LANGUAGES):
        for i, proto in enumerate(PROTOCOLS):
            vals = [idx[(lang, proto, "W1_list_songs", c)]["rps"] for c in concurrencies]
            rects = ax.bar(x + (i - 1.5) * width, vals, width, label=proto, color=COLORS[proto], zorder=3)
            add_bar_labels(ax, rects, fmt="{:.0f}", fontsize=8)
        ax.set_title(f"{lang}", fontsize=13, fontweight="bold", color="#0F172A", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.grid(axis="y", zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Throughput (req/s) — maior é melhor", fontsize=11, fontweight="bold", color="#334155")
    handles, leg_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, leg_labels, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, frameon=False, fontsize=11)
    fig.suptitle("Throughput (RPS) por Tecnologia e Linguagem (W1: Listagem de 100 Músicas)", fontsize=14, fontweight="bold", color="#0F172A", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(CHARTS_DIR / "02_throughput_rps_comparison.png", dpi=300)
    plt.close(fig)


def chart_03_workload_comparison(idx: Dict):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
    workloads = ["W1_list_songs", "W2_relational_profile", "W3_mixed_crud"]
    w_labels = ["W1: Listagem\n(100 músicas)", "W2: Perfil Relacional\n(User+Playlists+Songs)", "W3: Mix CRUD\n(70% R / 30% W)"]
    x = np.arange(len(workloads))
    width = 0.19

    for ax, lang in zip(axes, LANGUAGES):
        for i, proto in enumerate(PROTOCOLS):
            vals = [idx[(lang, proto, w, 50)]["p95_ms"] for w in workloads]
            rects = ax.bar(x + (i - 1.5) * width, vals, width, label=proto, color=COLORS[proto], zorder=3)
            add_bar_labels(ax, rects, fmt="{:.1f}", fontsize=8, auto_compact=True)
        ax.set_title(f"{lang} (50 VUs)", fontsize=13, fontweight="bold", color="#0F172A", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(w_labels, fontsize=9.5)
        ax.grid(axis="y", zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylim(0, axes[0].get_ylim()[1] * 1.12)

    axes[0].set_ylabel("Latência p95 (ms) — menor é melhor", fontsize=11, fontweight="bold", color="#334155")
    handles, leg_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, leg_labels, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, frameon=False, fontsize=11)
    fig.suptitle("Latência p95 por Tipo de Carga de Trabalho (Carga Moderada: 50 VUs)", fontsize=14, fontweight="bold", color="#0F172A", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(CHARTS_DIR / "03_workload_comparison_p95.png", dpi=300)
    plt.close(fig)


def chart_04_payload_size(idx: Dict):
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    workloads = ["W1_list_songs", "W2_relational_profile"]
    w_labels = ["W1: Listagem Completa (100 Músicas)", "W2: Perfil Relacional Completo"]
    x = np.arange(len(workloads))
    width = 0.18

    for i, proto in enumerate(PROTOCOLS):
        # Payload depende do formato de serialização do protocolo (média entre Python e Node)
        vals_kb = [
            np.mean([
                idx[("Python", proto, w, 50)]["avg_payload_bytes"],
                idx[("Node.js (TS)", proto, w, 50)]["avg_payload_bytes"],
            ]) / 1024.0
            for w in workloads
        ]
        rects = ax.bar(x + (i - 1.5) * width, vals_kb, width, label=proto, color=COLORS[proto], zorder=3)
        add_bar_labels(ax, rects, fmt="{:.2f} KB", fontsize=9)

    ax.set_ylabel("Tamanho Médio da Resposta (KB) — menor é melhor", fontsize=11, fontweight="bold", color="#334155")
    ax.set_title("Eficiência de Serialização: Tamanho do Payload (XML vs JSON vs Protobuf)", fontsize=13.5, fontweight="bold", color="#0F172A", pad=14)
    ax.set_xticks(x)
    ax.set_xticklabels(w_labels, fontsize=11)
    ax.grid(axis="y", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.5)
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "04_payload_size_comparison.png", dpi=300)
    plt.close(fig)


def chart_05_heatmap_8_implementations(idx: Dict):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))

    p95_mat = np.array([[idx[(lang, proto, "W1_list_songs", 50)]["p95_ms"] for proto in PROTOCOLS] for lang in LANGUAGES])
    rps_mat = np.array([[idx[(lang, proto, "W1_list_songs", 50)]["rps"] for proto in PROTOCOLS] for lang in LANGUAGES])

    im1 = axes[0].imshow(p95_mat, cmap="YlOrRd", aspect="auto")
    axes[0].set_title("Latência p95 (ms) — 50 VUs (menor = melhor)", fontsize=12, fontweight="bold", color="#0F172A", pad=10)
    axes[0].set_xticks(range(len(PROTOCOLS)))
    axes[0].set_xticklabels(PROTOCOLS, fontsize=11, fontweight="bold")
    axes[0].set_yticks(range(len(LANGUAGES)))
    axes[0].set_yticklabels(LANGUAGES, fontsize=11, fontweight="bold")
    for r in range(len(LANGUAGES)):
        for c in range(len(PROTOCOLS)):
            v = p95_mat[r, c]
            txt_color = "white" if v > (p95_mat.min() + 0.55 * (p95_mat.max() - p95_mat.min())) else "#0F172A"
            axes[0].text(c, r, f"{v:.1f} ms", ha="center", va="center", color=txt_color, fontsize=11, fontweight="bold")
    fig.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)

    im2 = axes[1].imshow(rps_mat, cmap="YlGn", aspect="auto")
    axes[1].set_title("Throughput (RPS) — 50 VUs (maior = melhor)", fontsize=12, fontweight="bold", color="#0F172A", pad=10)
    axes[1].set_xticks(range(len(PROTOCOLS)))
    axes[1].set_xticklabels(PROTOCOLS, fontsize=11, fontweight="bold")
    axes[1].set_yticks(range(len(LANGUAGES)))
    axes[1].set_yticklabels(LANGUAGES, fontsize=11, fontweight="bold")
    for r in range(len(LANGUAGES)):
        for c in range(len(PROTOCOLS)):
            v = rps_mat[r, c]
            txt_color = "white" if v > (rps_mat.min() + 0.55 * (rps_mat.max() - rps_mat.min())) else "#0F172A"
            axes[1].text(c, r, f"{v:.0f} req/s", ha="center", va="center", color=txt_color, fontsize=11, fontweight="bold")
    fig.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)

    fig.suptitle("Matriz Consolidada das 8 Implementações (4 Tecnologias × 2 Linguagens)", fontsize=14, fontweight="bold", color="#0F172A", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "05_heatmap_8_implementations.png", dpi=300)
    plt.close(fig)


def chart_06_percentiles_100vus(idx: Dict):
    fig, ax = plt.subplots(figsize=(13.5, 5.4))
    combos = [(lang, proto) for lang in LANGUAGES for proto in PROTOCOLS]
    x_labels = [f"{'Py' if l == 'Python' else 'Node'}\n{p}" for l, p in combos]
    x = np.arange(len(combos))
    width = 0.25

    p50 = [idx[(l, p, "W1_list_songs", 100)]["p50_ms"] for l, p in combos]
    p95 = [idx[(l, p, "W1_list_songs", 100)]["p95_ms"] for l, p in combos]
    p99 = [idx[(l, p, "W1_list_songs", 100)]["p99_ms"] for l, p in combos]

    r1 = ax.bar(x - width, p50, width, label="p50 (Mediana)", color="#38BDF8", zorder=3)
    r2 = ax.bar(x, p95, width, label="p95", color="#2563EB", zorder=3)
    r3 = ax.bar(x + width, p99, width, label="p99 (Cauda)", color="#1E3A8A", zorder=3)

    add_bar_labels(ax, r2, fmt="{:.0f}", fontsize=8.5)
    ax.axvline(3.5, color="#94A3B8", linestyle=":", linewidth=1.4)
    ax.text(1.5, ax.get_ylim()[1] * 0.93, "Python 3.12", ha="center", fontsize=11, fontweight="bold", color="#334155")
    ax.text(5.5, ax.get_ylim()[1] * 0.93, "Node.js 22 (TS)", ha="center", fontsize=11, fontweight="bold", color="#334155")

    ax.set_ylabel("Latência (ms) — menor é melhor", fontsize=11, fontweight="bold", color="#334155")
    ax.set_title("Distribuição de Latência (p50, p95 e p99) sob Carga Alta (100 VUs — W1)", fontsize=14, fontweight="bold", color="#0F172A", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=10, fontweight="bold")
    ax.grid(axis="y", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10)
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "06_percentiles_p50_p95_p99_100vus.png", dpi=300)
    plt.close(fig)


def chart_07_stress_saturation():
    if not STRESS_PATH.exists():
        return
    with STRESS_PATH.open("r", encoding="utf-8") as f:
        stress = json.load(f)

    points = stress["points"]
    sla_ms = stress["metadata"]["sla_p95_ms"]

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.5), sharey=True)

    for ax, lang in zip(axes, LANGUAGES):
        ax.axhline(sla_ms, color="#DC2626", linestyle="--", linewidth=1.6, zorder=2, label="Limite SLA (3000 ms)")
        for proto in PROTOCOLS:
            pts = [p for p in points if p["language"] == lang and p["protocol"] == proto]
            pts.sort(key=lambda x: x["concurrency"])
            xs = [p["concurrency"] for p in pts]
            ys = [p["p95_ms"] for p in pts]
            ax.plot(xs, ys, marker="o", linewidth=2.4, markersize=6, color=COLORS[proto], label=proto, zorder=4)

            # Offsets manuais limpos para evitar qualquer sobreposição de rótulos próximos
            offsets = {
                ("Python", "GraphQL"): (10, 14),
                ("Python", "REST"): (10, 0),
                ("Python", "SOAP"): (10, -14),
                ("Python", "gRPC"): (8, 6),
                ("Node.js (TS)", "SOAP"): (-30, 12),
                ("Node.js (TS)", "REST"): (10, 10),
                ("Node.js (TS)", "GraphQL"): (10, -12),
                ("Node.js (TS)", "gRPC"): (-165, 14),
            }
            dx, dy = offsets.get((lang, proto), (8, 6))

            # Marca ponto de ruptura com X vermelho ou badge de 1000 VUs
            last = pts[-1]
            if last["breached"]:
                ax.scatter([last["concurrency"]], [last["p95_ms"]], marker="X", s=130, color="#DC2626", edgecolors="white", linewidth=0.9, zorder=6)
                ax.annotate(
                    f"{proto}: {last['concurrency']} VUs ({last['p95_ms']:.0f} ms)",
                    xy=(last["concurrency"], last["p95_ms"]),
                    xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=8.2,
                    fontweight="bold",
                    color=COLORS[proto],
                )
            else:
                ax.annotate(
                    f"{proto}: OK em 1000 VUs ({last['p95_ms']:.0f} ms)",
                    xy=(last["concurrency"], last["p95_ms"]),
                    xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=8.5,
                    fontweight="bold",
                    color=COLORS[proto],
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=COLORS[proto], alpha=0.9),
                )

        ax.set_title(f"{lang}", fontsize=13, fontweight="bold", color="#0F172A", pad=10)
        ax.set_xlabel("Usuários Virtuais Concorrentes (VUs)", fontsize=10.5, fontweight="bold", color="#334155")
        ax.set_xlim(0, 1080)
        ax.set_ylim(0, 5300)
        ax.grid(True, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Latência p95 (ms) — ruptura em ≥ 3000 ms", fontsize=11, fontweight="bold", color="#334155")
    handles, leg_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, leg_labels, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=5, frameon=False, fontsize=10.5)
    fig.suptitle("Teste de Estresse até o Limite (Curva de Saturação: 10 → 1000 VUs | W1)", fontsize=14, fontweight="bold", color="#0F172A", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(CHARTS_DIR / "07_stress_saturation_curves.png", dpi=300)
    plt.close(fig)


def main():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_results()
    idx = index_results(rows)

    chart_01_p95_by_concurrency(idx)
    chart_02_throughput_by_concurrency(idx)
    chart_03_workload_comparison(idx)
    chart_04_payload_size(idx)
    chart_05_heatmap_8_implementations(idx)
    chart_06_percentiles_100vus(idx)
    chart_07_stress_saturation()

    print("Gráficos gerados com sucesso em", CHARTS_DIR)


if __name__ == "__main__":
    main()
