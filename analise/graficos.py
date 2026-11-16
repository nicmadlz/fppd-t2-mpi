#!/usr/bin/env python3
import csv, os, sys, statistics as st
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
figs = os.path.join(raiz, "relatorio", "figs"); os.makedirs(figs, exist_ok=True)

rows = list(csv.DictReader(open(os.path.join(raiz, "dados", "resultados.csv"), encoding="utf-8")))
procs = list(csv.DictReader(open(os.path.join(raiz, "dados", "processos.csv"), encoding="utf-8")))
FASES = ["geracao", "distribuicao", "calculo", "coleta"]
por = defaultdict(list)
for r in rows:
    por[r["config"]].append(r)
f = lambda cfg, k: [float(r[k]) for r in por[cfg]]
med = lambda cfg, k: st.median(f(cfg, k))

T1 = med("sequencial", "total")
s = med("sequencial", "geracao") / T1
teto = 1 / s

ESCAL = ["par_1x2", "par_1x4", "par_1x6", "par_1x8", "par_2x8", "par_4x8"]
REDE = ["par_1x8", "par_2x4", "par_4x2"]
PNUC = ["par_1x8", "par_1x16", "par_1x32"]
ordem = ["sequencial"] + ESCAL + ["par_2x4", "par_4x2", "par_1x16", "par_1x32"]
nome = lambda c: "sequencial" if c == "sequencial" else c[4:]

resumo = []
for c in ordem:
    if c not in por: continue
    tot = f(c, "total"); p = int(por[c][0]["processos"]); n = int(por[c][0]["nos"])
    su = T1 / st.median(tot)
    resumo.append(dict(config=nome(c), nos=n, processos=p, mediana=st.median(tot), minimo=min(tot),
                       maximo=max(tot), speedup=su, eficiencia=su / p, reps=len(tot)))
with open(os.path.join(raiz, "dados", "resumo.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(resumo[0])); w.writeheader(); w.writerows(resumo)

xs = [int(por[c][0]["processos"]) for c in ESCAL if c in por]
cs = [c for c in ESCAL if c in por]
su = [T1 / med(c, "total") for c in cs]
amd = lambda n: 1 / (s + (1 - s) / n)
grade = [2 ** (i / 8) for i in range(0, 8 * 5 + 1)]
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.plot(grade, grade, "--", color="gray", label="speedup ideal")
ax.plot(grade, [amd(n) for n in grade], "-", color="tab:red", label=f"Amdahl (s={s:.4f})")
ax.axhline(teto, color="tab:red", ls=":", label=f"teto 1/s = {teto:.0f}")
lo = [T1 / max(f(c, "total")) for c in cs]; hi = [T1 / min(f(c, "total")) for c in cs]
ax.errorbar(xs, su, yerr=[[a - b for a, b in zip(su, lo)], [b - a for a, b in zip(su, hi)]],
            fmt="o-", color="tab:blue", capsize=3, label="medido (mediana; barras: mín/máx)")
ax.set_xscale("log", base=2); ax.set_yscale("log", base=2)
ax.set_ylim(0.8, teto * 1.5); ax.set_xticks(xs); ax.set_xticklabels(xs); ax.set_xlabel("processos"); ax.set_ylabel("speedup")
ax.grid(True, which="both", alpha=.3); ax.legend(fontsize=7); fig.tight_layout()
fig.savefig(os.path.join(figs, "speedup.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(5.2, 3.0))
ax.plot(xs, [a / b for a, b in zip(su, xs)], "o-")
ax.set_xscale("log", base=2); ax.set_xticks(xs); ax.set_xticklabels(xs)
ax.set_xlabel("processos"); ax.set_ylabel("eficiência"); ax.set_ylim(0, 1.1); ax.grid(True, alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(figs, "eficiencia.png"), dpi=200); plt.close(fig)

def fases(lista, arq, titulo):
    cs = [c for c in lista if c in por]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    base = [0] * len(cs)
    for k in FASES:
        v = [med(c, k) for c in cs]
        ax.bar([nome(c) for c in cs], v, bottom=base, label=k)
        base = [a + b for a, b in zip(base, v)]
    ax.set_ylabel("tempo (s, mediana)"); ax.set_title(titulo, fontsize=9); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(figs, arq), dpi=200); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    larg = 0.25
    for i, k in enumerate(["distribuicao", "coleta"]):
        ax.bar([j + (i - .5) * larg * 1.5 for j in range(len(cs))], [med(c, k) for c in cs], larg, label=k)
    ax.set_xticks(range(len(cs))); ax.set_xticklabels([nome(c) for c in cs])
    ax.set_ylabel("tempo (s, mediana)"); ax.legend(fontsize=7); ax.set_title(titulo + ": distribuição e coleta", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(figs, arq.replace(".png", "_comm.png")), dpi=200); plt.close(fig)

fases(REDE, "fases_rede.png", "Série de rede (8 processos)")
fases(PNUC, "fases_pnuc.png", "Série de processos por núcleo (1 nó)")

def por_rank(cfg):
    d = defaultdict(list)
    for p in procs:
        if p["config"] == cfg: d[int(p["rank"])].append(float(p["calculo"]))
    return {r: st.median(v) for r, v in sorted(d.items())}
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
for ax, c in zip(axs, ["par_1x8", "par_4x8", "par_1x32"]):
    if c not in por: continue
    d = por_rank(c); ax.bar(list(d), list(d.values()), color="tab:blue")
    ax.set_title(nome(c), fontsize=9); ax.set_xlabel("rank"); ax.set_ylabel("cálculo (s)")
fig.tight_layout(); fig.savefig(os.path.join(figs, "calc_por_rank.png"), dpi=200); plt.close(fig)

if True:
    fh = sys.stdout
    fh.write(f"T1 (mediana sequencial total) = {T1:.3f} s\n")
    fh.write(f"geração sequencial (mediana)  = {med('sequencial','geracao'):.3f} s\n")
    fh.write(f"fração sequencial s            = {s:.6f}\nteto de Amdahl 1/s             = {teto:.1f}\n\n")
    fh.write("config  total_med  speedup  efic  | calc_min/max entre processos (mediana das reps)  | dist  coleta\n")
    for c in ordem[1:]:
        if c not in por: continue
        p = int(por[c][0]["processos"]); sp = T1 / med(c, "total")
        fh.write(f"{nome(c):6s} {med(c,'total'):8.2f} {sp:8.2f} {sp/p:6.2f} | {med(c,'calc_min'):7.2f} / {med(c,'calc_max'):7.2f} | {med(c,'distribuicao'):6.2f} {med(c,'coleta'):6.2f}\n")
    fh.write("\nVariação entre repetições (máx/mín do total):\n")
    for c in ordem:
        if c in por: fh.write(f"{nome(c):10s} {max(f(c,'total'))/min(f(c,'total')):.3f}\n")
    fh.write("\nSpeedup > p ou acima de Amdahl?\n")
    for c in ordem[1:]:
        if c not in por: continue
        p = int(por[c][0]["processos"]); sp = T1 / med(c, "total")
        fh.write(f"{nome(c):6s} p={p:3d} su={sp:6.2f} amdahl={amd(p):6.2f} {'SUPERLINEAR' if sp>p else ''} {'ACIMA_AMDAHL' if sp>amd(p) else ''}\n")

