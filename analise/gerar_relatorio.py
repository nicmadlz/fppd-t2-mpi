#!/usr/bin/env python3
import csv, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, KeepTogether

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
figs = os.path.join(raiz, "relatorio", "figs")

CONTAS = "[PREENCHER: fppd3xxxx, ...]"
GRUPO = "Nícolas Azambuja, Rodrigo Ferreira, João Gabriel Cirne, Eduardo Auler"
PEND = "[PREENCHER após as medições, com base em relatorio/numeros.txt]"
RESPOSTAS = {
    1: ("Fração sequencial e teto de Amdahl",
        "A fração sequencial medida é s = (tempo de geração) / (tempo total do sequencial). " + PEND +
        " Comparar o teto 1/s com o speedup medido em 4×8 e explicar a distância (distribuição de B, coleta, "
        "contenção de banda de memória, desbalanceamento)."),
    2: ("Menor tempo, melhor eficiência e sweet spot", PEND),
    3: ("Série de rede (1×8, 2×4, 4×2)",
        PEND + " Citar as fases em que a diferença aparece e o outro complicador (contenção de memória / desbalanceamento)."),
    4: ("Série de processos por núcleo (1×8, 1×16, 1×32)",
        PEND + " Discutir 8→16 (Hyper-Threading) e 16→32 (mais processos que threads)."),
    5: ("Tempo de cálculo por processo", PEND + " Usar dados/processos.csv e a figura de cálculo por processo."),
    6: ("Resultados inesperados",
        PEND + " Verificar speedup > p, acima do teto de Amdahl e variação máx/mín entre repetições."),
}

ss = getSampleStyleSheet()
corpo = ParagraphStyle("c", parent=ss["BodyText"], fontSize=9, leading=11.5, spaceAfter=4)
h1 = ParagraphStyle("h1", parent=ss["Heading2"], fontSize=11.5, spaceBefore=6, spaceAfter=3)
tit = ParagraphStyle("t", parent=ss["Title"], fontSize=15, spaceAfter=4)
peq = ParagraphStyle("p", parent=corpo, fontSize=8, leading=10)
P = lambda t, s=corpo: Paragraph(t, s)

el = [P("T2: Processamento Paralelo com MPI", tit),
      P("FPPD · Multiplicação de matrizes 5000×5000 em Go + MPI no cluster Atlântica", ss["Normal"]),
      P(f"<b>Grupo:</b> {GRUPO}. <b>Contas do LAD usadas nos experimentos:</b> {CONTAS}.")]

el += [P("1. Versão paralela", h1),
       P("<b>Divisão do trabalho.</b> Decomposição de domínio (PCAM) por blocos contíguos de linhas de A e de C: com p processos, "
         "cada um recebe N/p linhas e os N mod p primeiros recebem uma linha a mais, o que vale para qualquer p. Como o custo por linha é uniforme, "
         "o mapeamento é estático. Cada processo calcula suas linhas de C com a função <i>multiplica</i> do sequencial, sem alteração, e o rank 0 também calcula seu bloco."),
       P("<b>Comunicação.</b> Só o rank 0 gera A e B (mesma semente do sequencial). B, de 200 MB, vai a todos por uma árvore binomial de Send/Recv "
         "(⌈log₂ p⌉ rodadas), em pedaços de 8 MiB; o rank 0 envia a cada processo seu bloco de A. Na coleta, cada processo envia seu bloco de C ao rank 0, "
         "que o recebe diretamente na posição final de C e chama <i>verifica</i> (mesmos cantos e checksum do sequencial). Só Send e Recv do gompi são usados."),
       P("<b>Medição.</b> Cada fase é delimitada por <i>Barrier</i> e <i>mpi.WTime</i>: geração, distribuição (B e A), cálculo e coleta. "
         "O tempo total vai do início da geração ao fim da coleta, e as barreiras fazem com que ele corresponda ao processo mais lento. "
         "Cada processo mede o próprio tempo de cálculo, enviado ao rank 0 após a região medida. A verificação não entra no tempo, como no sequencial.")]

el += [P("2. Experimentos", h1),
       P("Todas as medições são jobs <i>sbatch</i> com nó exclusivo no Atlântica (8 núcleos físicos, 16 threads por nó), N = 5000, "
         "10 repetições por configuração (reportadas: mediana, mínimo, máximo). Speedup e eficiência usam como T₁ a mediana do tempo total do sequencial. "
         "A fração sequencial vem do tempo de geração do sequencial. Séries: escalabilidade (1×2, 1×4, 1×6, 1×8, 2×8, 4×8), rede (1×8, 2×4, 4×2) e "
         "processos por núcleo (1×8, 1×16, 1×32, com <i>--oversubscribe</i>). Saídas dos jobs, scripts e CSV acompanham a entrega.")]

resumo = os.path.join(raiz, "dados", "resumo.csv")
el.append(P("3. Resultados", h1))
if os.path.exists(resumo):
    linhas = [["Config.", "Nós", "Proc.", "Mediana (s)", "Mín (s)", "Máx (s)", "Speedup", "Efic."]]
    for r in csv.DictReader(open(resumo, encoding="utf-8")):
        linhas.append([r["config"], r["nos"], r["processos"], f"{float(r['mediana']):.2f}", f"{float(r['minimo']):.2f}",
                       f"{float(r['maximo']):.2f}", f"{float(r['speedup']):.2f}", f"{float(r['eficiencia']):.2f}"])
    t = Table(linhas, hAlign="CENTER")
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), .3, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
    el += [t, P("Tabela 1: tempo total (N = 5000), speedup e eficiência em relação ao sequencial.", peq)]
else:
    el.append(P("[Tabela 1: gerada por analise/graficos.py quando houver dados]"))


def fig(nome, legenda, larg):
    p = os.path.join(figs, nome)
    if not os.path.exists(p):
        return [P(f"[{legenda}: aguardando dados]", peq)]
    w, h = ImageReader(p).getSize()
    return [KeepTogether([Image(p, larg * cm, larg * cm * h / w), P(legenda, peq)])]


el += fig("speedup.png", "Figura 1: speedup (log-log) com reta ideal e teto de Amdahl.", 8.5)
el += fig("eficiencia.png", "Figura 2: eficiência da série de escalabilidade.", 8.0)
el += fig("fases_rede.png", "Figura 3: tempo por fase na série de rede.", 8.0)
el += fig("fases_pnuc.png", "Figura 4: tempo por fase na série de processos por núcleo.", 8.0)
el += fig("calc_por_rank.png", "Figura 5: tempo de cálculo por processo.", 12.0)

el.append(P("4. Respostas", h1))
for k, (titulo, txt) in RESPOSTAS.items():
    el.append(P(f"<b>{k}. {titulo}.</b> {txt}"))

el += [P("5. Uso de ferramentas de IA", h1),
       P("Foi usado o Claude (Anthropic), via Claude Code, nas seguintes etapas: <b>pesquisa</b> (leitura do enunciado, do pacote gompi e dos exemplos do lad-go-mpi), "
         "<b>implementação inicial</b> da versão paralela, geração dos scripts de job e dos scripts de análise (parse e gráficos) e rascunho da estrutura deste relatório. "
         "O código foi testado localmente com um MPI simulado, as medições foram executadas pelo grupo no cluster e a análise e as conclusões foram feitas pelo grupo a partir dos dados medidos. "
         "[CONFERIR: o grupo deve ajustar este parágrafo ao que de fato fez.]"),
       P("6. Referências", h1),
       P("[1] Material das Aulas 17, 18 e 19 de FPPD (PUCRS): MPI em Go, métricas de desempenho, utilização do cluster do LAD.<br/>"
         "[2] mvneves/gompi e mvneves/lad-go-mpi, github.com.<br/>"
         "[3] Documentação do LAD, lad-pucrs.github.io/docs.<br/>"
         "[4] I. Foster. <i>Designing and Building Parallel Programs</i>. Addison-Wesley, 1995 (metodologia PCAM).<br/>"
         "[5] G. Amdahl. Validity of the single processor approach to achieving large scale computing capabilities. AFIPS, 1967.<br/>"
         "[6] Open MPI, open-mpi.org (documentação do mpirun e de <i>--oversubscribe</i>).", peq)]

SimpleDocTemplate(os.path.join(raiz, "relatorio", "relatorio.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                  topMargin=1.7 * cm, bottomMargin=1.7 * cm, title="T2 FPPD").build(el)
print("relatorio/relatorio.pdf gerado")
