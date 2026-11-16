#!/usr/bin/env python3
import csv, glob, os, re, sys

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(raiz, "saidas")
dados = os.path.join(raiz, "dados")
os.makedirs(dados, exist_ok=True)

num = r"([0-9]+\.[0-9]+)"
rx_seq = {
    "geracao": re.compile(r"Tempo de geração:\s+" + num),
    "calculo": re.compile(r"Tempo de multiplicação:\s+" + num),
    "total": re.compile(r"Tempo total:\s+" + num),
}
rx_fases = re.compile(r"FASES geracao=%s distribuicao=%s calculo=%s coleta=%s total=%s" % ((num,) * 5))
rx_proc = re.compile(r"PROCESSO rank=(\d+) host=(\S+) linhas=(\d+) calculo=" + num)
rx_sum = re.compile(r"Checksum\s+=\s+(\S+)")
rx_job = re.compile(r"^Job:\s+(\d+)", re.M)
rx_nos = re.compile(r"^Nós:\s+(.*)$", re.M)

runs, procs, avisos = [], [], []

for arq in sorted(glob.glob(os.path.join(pasta, "*.out"))):
    base = os.path.basename(arq)
    m = re.match(r"(sequencial|par_(\d+)x(\d+))\.(\d+)\.out$", base)
    if not m:
        continue
    cfg, nos, ppn, job = m.group(1), m.group(2), m.group(3), m.group(4)
    nos, ppn = (1, 1) if cfg == "sequencial" else (int(nos), int(ppn))
    txt = open(arq, encoding="utf-8").read()
    lista_nos = (rx_nos.search(txt).group(1).strip() if rx_nos.search(txt) else "")
    blocos = re.split(r"^== Repetição (\d+)\s*$", txt, flags=re.M)
    for i in range(1, len(blocos), 2):
        rep, corpo = int(blocos[i]), blocos[i + 1]
        cs = rx_sum.search(corpo)
        if cfg == "sequencial":
            t = {k: rx_seq[k].search(corpo) for k in rx_seq}
            if not all(t.values()):
                avisos.append(f"{base} rep {rep}: saída incompleta"); continue
            row = dict(geracao=float(t["geracao"].group(1)), distribuicao=0.0,
                       calculo=float(t["calculo"].group(1)), coleta=0.0,
                       total=float(t["total"].group(1)), calc_min=float(t["calculo"].group(1)),
                       calc_max=float(t["calculo"].group(1)))
        else:
            f = rx_fases.search(corpo)
            ps = rx_proc.findall(corpo)
            if not f or not ps:
                avisos.append(f"{base} rep {rep}: saída incompleta"); continue
            g, d, c, co, tot = map(float, f.groups())
            calcs = [float(p[3]) for p in ps]
            row = dict(geracao=g, distribuicao=d, calculo=c, coleta=co, total=tot,
                       calc_min=min(calcs), calc_max=max(calcs))
            for r, host, linhas, tc in ps:
                procs.append(dict(config=cfg, repeticao=rep, job=job, rank=int(r), host=host,
                                  linhas=int(linhas), calculo=float(tc)))
        row.update(config=cfg, nos=nos, processos=nos * ppn, repeticao=rep, job=job,
                   nodelist=lista_nos, checksum=cs.group(1) if cs else "")
        runs.append(row)

cols = ["config", "nos", "processos", "repeticao", "job", "nodelist", "geracao", "distribuicao",
        "calculo", "coleta", "total", "calc_min", "calc_max", "checksum"]
with open(os.path.join(dados, "resultados.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(runs)
with open(os.path.join(dados, "processos.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["config", "repeticao", "job", "rank", "host", "linhas", "calculo"])
    w.writeheader(); w.writerows(procs)

esperadas = ["sequencial", "par_1x2", "par_1x4", "par_1x6", "par_1x8", "par_2x8", "par_4x8",
             "par_2x4", "par_4x2", "par_1x16", "par_1x32"]
for c in esperadas:
    n = sum(1 for r in runs if r["config"] == c)
    if n < 10:
        avisos.append(f"{c}: {n} repetições válidas (mínimo 10)")
somas = {r["checksum"] for r in runs}
if len(somas) != 1:
    avisos.append(f"checksums divergentes: {sorted(somas)}")
print(f"{len(runs)} execuções, {len(procs)} registros de processo -> dados/")
for a in avisos:
    print("AVISO:", a)
