"""Gera as figuras e tabelas do relatório em docs/recursos/.

Reaproveita as funções do analise.py (carregar, estatisticas, dados, regressao),
então os números do relatório são os mesmos da análise. Rode da raiz do repo:

    venv/bin/python docs/gerar_recursos.py

Sempre que novos CSVs forem gerados (ex.: pior caso com n = 1.000.000),
rode de novo e recompile o relatório.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy import stats

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import analise  # noqa: E402  (carregar, estatisticas, dados, regressao)

# ====================== CONFIGURAÇÃO ======================
RECURSOS = AQUI / "recursos"
FIGURAS = RECURSOS / "figuras"
TABELAS = RECURSOS / "tabelas"
DADOS = RECURSOS / "dados"

ALGORITMOS = analise.ALGORITMOS
CENARIOS = analise.CENARIOS
NOME_ALG = {"insertion": "Insertion Sort", "merge": "Merge Sort"}
NOME_CEN = {"melhor": "melhor caso", "medio": "caso médio", "pior": "pior caso"}
CORES = {"insertion": "#C0392B", "merge": "#2E5E9E"}
GRAUS = analise.GRAUS_REGRESSAO
ALFA = 0.05                       # nível de significância dos testes
# ==========================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.formatter.use_locale": False,
})


# ---------- utilidades de formatação ----------
def br(texto):
    """Troca o ponto decimal por vírgula (padrão brasileiro)."""
    return texto.replace(".", "{,}")


def num(x, sig=4):
    """Número com 'sig' algarismos significativos, sem notação científica."""
    if x == 0 or not np.isfinite(x):
        return "0"
    casas = max(sig - 1 - int(np.floor(np.log10(abs(x)))), 0)
    return f"{x:.{casas}f}"


def cientifico(x, sig=4):
    """Número em notação científica para o siunitx: 6.683e-11."""
    return f"{x:.{sig - 1}e}"


def milhar(n):
    """1000000 -> 1.000.000 (separador de milhar brasileiro)."""
    return f"{n:,}".replace(",", ".")


def eixo_n(ax, ns):
    ax.set_xticks(np.arange(len(ns)))
    ax.set_xticklabels([milhar(n) for n in ns], rotation=45, ha="right")


def coluna_S(valores):
    """Coluna do siunitx com largura suficiente para alinhar pelo separador decimal."""
    inteiros = max(len(v.split(".")[0].lstrip("-")) for v in valores)
    decimais = max((len(v.split(".")[1]) if "." in v else 0) for v in valores)
    return f"S[table-format={inteiros}.{decimais}]"


def salvar_tabela(nome, linhas):
    (TABELAS / nome).write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ---------- 1. Tabelas de estatísticas (uma por algoritmo × cenário) ----------
def tabelas_estatisticas(r):
    """Média, desvio, IC 95 %, mínimo e máximo em milissegundos."""
    for alg in ALGORITMOS:
        for cen in CENARIOS:
            d = analise.dados(r, alg, cen)
            if d.empty:
                continue
            campos = ("media", "desvio", "ic95", "minimo", "maximo")
            valores = [[num(l[c] * 1e3) for c in campos] for _, l in d.iterrows()]
            formatos = " ".join(coluna_S([v[i] for v in valores]) for i in range(len(campos)))
            linhas = [
                r"\begin{tabular}{r " + formatos + " r}",
                r"\toprule",
                r"{$n$} & {Média} & {Desvio padrão} & {IC 95\,\% ($\pm$)}"
                r" & {Mínimo} & {Máximo} & {Rep.} \\",
                r"\midrule",
            ]
            for (_, l), v in zip(d.iterrows(), valores):
                linhas.append(f"{milhar(int(l['n']))} & " + " & ".join(v)
                              + f" & {int(l['reps'])} \\\\")
            linhas += [r"\bottomrule", r"\end{tabular}"]
            salvar_tabela(f"estatisticas_{alg}_{cen}.tex", linhas)


# ---------- 2. Gráficos comparativos (os 3 exigidos no enunciado) ----------
def grafico_comparativo(r, cen):
    d = r[r["cenario"] == cen]
    ns = sorted(d["n"].unique())
    x = np.arange(len(ns))
    larg = 0.4

    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    for i, alg in enumerate(ALGORITMOS):
        s = d[d["algoritmo"] == alg].set_index("n").reindex(ns)
        ax.bar(x + (i - 0.5) * larg, s["media"], larg, yerr=s["ic95"],
               capsize=2.5, error_kw={"elinewidth": 0.8, "capthick": 0.8},
               color=CORES[alg], label=NOME_ALG[alg], zorder=2)
    eixo_n(ax, ns)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$10^{{{int(np.log10(v))}}}$"))
    ax.grid(axis="y", which="major", alpha=0.3, zorder=0)
    ax.set_xlabel("Tamanho da entrada ($n$)")
    ax.set_ylabel("Tempo médio de execução (s, escala log)")
    ax.set_title(f"Tempo médio de execução: {NOME_CEN[cen]}")
    ax.legend(title="Algoritmo (média ± IC 95%)", frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURAS / f"comparativo_{cen}.pdf")
    plt.close(fig)


# ---------- 3. Comparação entre algoritmos (significância) ----------
def comparacao(df, r):
    """Para cada cenário e n: razão Insertion/Merge, sobreposição dos IC e teste de Welch."""
    linhas_csv = []
    for cen in CENARIOS:
        d = r[r["cenario"] == cen]
        ns = sorted(set(d[d["algoritmo"] == "insertion"]["n"]) & set(d[d["algoritmo"] == "merge"]["n"]))
        if not ns:
            continue
        corpo = []
        for n in ns:
            ins = d[(d["algoritmo"] == "insertion") & (d["n"] == n)].iloc[0]
            mer = d[(d["algoritmo"] == "merge") & (d["n"] == n)].iloc[0]
            ti = df[(df["algoritmo"] == "insertion") & (df["cenario"] == cen) & (df["n"] == n)]["tempo_s"]
            tm = df[(df["algoritmo"] == "merge") & (df["cenario"] == cen) & (df["n"] == n)]["tempo_s"]
            p = stats.ttest_ind(ti, tm, equal_var=False).pvalue
            sobrepoe = (ins["media"] - ins["ic95"] <= mer["media"] + mer["ic95"]
                        and mer["media"] - mer["ic95"] <= ins["media"] + ins["ic95"])
            significativa = p < ALFA and not sobrepoe
            razao = ins["media"] / mer["media"]
            corpo.append([milhar(n), num(ins["media"] * 1e3), num(mer["media"] * 1e3), num(razao, 3),
                          "Sim" if sobrepoe else "Não", "Sim" if significativa else "Não"])
            linhas_csv.append({"cenario": cen, "n": n, "insertion_s": ins["media"],
                               "merge_s": mer["media"], "razao_I_M": razao,
                               "ic_sobrepoem": sobrepoe, "p_welch": p,
                               "significativa": significativa})
        formatos = " ".join(coluna_S([c[i] for c in corpo]) for i in (1, 2, 3))
        linhas = [
            r"\begin{tabular}{r " + formatos + " c c}",
            r"\toprule",
            r"{$n$} & {Insertion (ms)} & {Merge (ms)} & {Razão I/M}"
            r" & {IC se sobrepõem?} & {Diferença significativa?} \\",
            r"\midrule",
        ]
        linhas += [" & ".join(c) + r" \\" for c in corpo]
        linhas += [r"\bottomrule", r"\end{tabular}"]
        salvar_tabela(f"comparacao_{cen}.tex", linhas)
    pd.DataFrame(linhas_csv).to_csv(DADOS / "comparacao.csv", index=False)


# ---------- 4. Razão T(2n)/T(n) ----------
def razao_esperada(alg, cen, n):
    if alg == "insertion":
        return 2.0 if cen == "melhor" else 4.0
    return 2 * np.log2(2 * n) / np.log2(n)          # n log n


def razao_dobro(r):
    linhas_csv = []
    for alg in ALGORITMOS:
        for cen in CENARIOS:
            m = analise.dados(r, alg, cen).set_index("n")["media"]
            for n in m.index:
                if 2 * n in m.index:
                    linhas_csv.append({"algoritmo": alg, "cenario": cen, "n": n, "2n": 2 * n,
                                       "razao": m[2 * n] / m[n],
                                       "esperada": razao_esperada(alg, cen, n)})
    rz = pd.DataFrame(linhas_csv)
    rz.to_csv(DADOS / "razao_dobro.csv", index=False)

    pares = sorted(set(rz["n"]))
    colunas = [(a, c) for a in ALGORITMOS for c in CENARIOS
               if not rz[(rz["algoritmo"] == a) & (rz["cenario"] == c)].empty]
    linhas = [
        r"\begin{tabular}{l " + "S[table-format=1.2] " * len(colunas) + "}",
        r"\toprule",
        r" & " + " & ".join(
            r"\multicolumn{" + str(sum(1 for a, _ in colunas if a == alg)) + r"}{c}{" + NOME_ALG[alg] + "}"
            for alg in ALGORITMOS if any(a == alg for a, _ in colunas)) + r" \\",
    ]
    inicio = 2
    regras = []
    for alg in ALGORITMOS:
        k = sum(1 for a, _ in colunas if a == alg)
        if k:
            regras.append(rf"\cmidrule(lr){{{inicio}-{inicio + k - 1}}}")
            inicio += k
    linhas.append("".join(regras))
    linhas.append(r"{$n \to 2n$} & " + " & ".join("{" + NOME_CEN[c].capitalize() + "}" for _, c in colunas) + r" \\")
    linhas.append(r"\midrule")
    for n in pares:
        valores = []
        for a, c in colunas:
            s = rz[(rz["algoritmo"] == a) & (rz["cenario"] == c) & (rz["n"] == n)]
            valores.append(num(s["razao"].iloc[0], 3) if not s.empty else "{--}")
        linhas.append(f"{milhar(n)} $\\to$ {milhar(2 * n)} & " + " & ".join(valores) + r" \\")
    linhas.append(r"\midrule")
    esperadas = []
    for a, c in colunas:
        if a == "merge":
            esperadas.append(r"{$\approx 2{,}1$}")
        else:
            esperadas.append(num(razao_esperada(a, c, 1000), 2))
    linhas.append(r"Esperada (teoria) & " + " & ".join(esperadas) + r" \\")
    linhas += [r"\bottomrule", r"\end{tabular}"]
    salvar_tabela("razao_dobro.tex", linhas)


# ---------- 5. Regressão polinomial (+ modelo n log n para comparação) ----------
def ajuste_nlogn(d):
    """Mínimos quadrados para T(n) = a·n·log2(n) + b."""
    n = d["n"].to_numpy(float)
    y = d["media"].to_numpy(float)
    X = np.column_stack([n * np.log2(n), np.ones_like(n)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    return coef, r2


def coef_em_n(coef_x):
    """analise.regressao usa x = n/1e6; converte para coeficientes em n."""
    grau = len(coef_x) - 1
    return [c / 1e6 ** (grau - i) for i, c in enumerate(coef_x)]


def latex_polinomio(coef_n):
    grau = len(coef_n) - 1
    termos = []
    for i, c in enumerate(coef_n):
        p = grau - i
        sinal = "-" if c < 0 else "+"
        valor = rf"\num{{{cientifico(abs(c))}}}"
        base = "" if p == 0 else ("n" if p == 1 else f"n^{p}")
        termos.append((sinal, valor + (r"\," + base if base else "")))
    texto = ("-" if termos[0][0] == "-" else "") + termos[0][1]
    for sinal, t in termos[1:]:
        texto += f" {sinal} {t}"
    return f"${texto}$"


def regressoes(r):
    """Uma tabela por algoritmo: polinômios de grau 1 a 3 (e n log n no Merge) com R²."""
    linhas_csv = []
    for alg in ALGORITMOS:
        linhas = [
            r"\begin{tabular}{l l l S[table-format=1.6]}",
            r"\toprule",
            r"Cenário & Modelo & {Função obtida, $T(n)$ em segundos} & {$R^2$} \\",
            r"\midrule",
        ]
        primeira = True
        for cen in CENARIOS:
            d = analise.dados(r, alg, cen)
            if d.empty:
                continue
            if not primeira:
                linhas.append(r"\midrule")
            primeira = False
            for g in GRAUS:
                coef_x, r2 = analise.regressao(r, alg, cen, g)
                cn = coef_em_n(coef_x)
                linhas.append(f"{NOME_CEN[cen].capitalize()} & Grau {g} & "
                              f"{latex_polinomio(cn)} & {r2:.6f} \\\\")
                linhas_csv.append({"algoritmo": alg, "cenario": cen, "modelo": f"grau {g}",
                                   "coeficientes_n": [float(c) for c in cn], "R2": r2})
            if alg == "merge":
                (a, b), r2 = ajuste_nlogn(d)
                linhas.append(f"{NOME_CEN[cen].capitalize()} & $n\\log_2 n$ & "
                              rf"$\num{{{cientifico(a)}}}\,n\log_2 n "
                              rf"{'-' if b < 0 else '+'} \num{{{cientifico(abs(b))}}}$ & {r2:.6f} \\")
                linhas_csv.append({"algoritmo": alg, "cenario": cen, "modelo": "n log2 n",
                                   "coeficientes_n": [float(a), float(b)], "R2": r2})
        linhas += [r"\bottomrule", r"\end{tabular}"]
        salvar_tabela(f"regressao_{alg}.tex", linhas)
    pd.DataFrame(linhas_csv).to_csv(DADOS / "regressoes.csv", index=False)


def grafico_regressao(r, cen):
    """Médias observadas (com IC) e curvas ajustadas, um painel por algoritmo."""
    algs = [a for a in ALGORITMOS if not analise.dados(r, a, cen).empty]
    if not algs:
        return
    fig, eixos = plt.subplots(1, len(algs), figsize=(6.3, 2.9))
    eixos = np.atleast_1d(eixos)
    estilos = {1: ":", 2: "--", 3: "-."}
    for ax, alg in zip(eixos, algs):
        d = analise.dados(r, alg, cen)
        n = d["n"].to_numpy(float)
        grade = np.linspace(n.min(), n.max(), 300)
        ax.errorbar(n / 1e3, d["media"], yerr=d["ic95"], fmt="o", ms=3.5,
                    color=CORES[alg], capsize=2, label="Média observada", zorder=3)
        for g in GRAUS:
            coef_x, r2 = analise.regressao(r, alg, cen, g)
            ax.plot(grade / 1e3, np.polyval(coef_x, grade / 1e6), estilos[g], lw=1,
                    color="0.25", label=f"Grau {g} ($R^2$={r2:.4f})".replace(".", ","))
        if alg == "merge":
            (a, b), r2 = ajuste_nlogn(d)
            ax.plot(grade / 1e3, a * grade * np.log2(grade) + b, "-", lw=1, color="#E67E22",
                    label=f"$a\\,n\\log_2 n+b$ ($R^2$={r2:.4f})".replace(".", ","))
        ax.set_title(NOME_ALG[alg])
        ax.set_xlabel("$n$ (milhares)")
        ax.set_ylabel("Tempo médio (s)")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=6.5)
    fig.suptitle(f"Regressão polinomial: {NOME_CEN[cen]}", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURAS / f"regressao_{cen}.pdf")
    plt.close(fig)


# ---------- 6. Expoente empírico (inclinação no gráfico log-log) ----------
def expoentes(r):
    linhas_csv = []
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    marcadores = {"melhor": "o", "medio": "s", "pior": "^"}
    for alg in ALGORITMOS:
        for cen in CENARIOS:
            d = analise.dados(r, alg, cen)
            if d.empty:
                continue
            ln, lt = np.log10(d["n"]), np.log10(d["media"])
            k, c = np.polyfit(ln, lt, 1)
            # inclinação que um T exatamente n log n teria nesses mesmos valores de n
            k_nlogn = np.polyfit(ln, np.log10(d["n"] * np.log2(d["n"])), 1)[0]
            linhas_csv.append({"algoritmo": alg, "cenario": cen, "expoente": k,
                               "esperado_nlogn": k_nlogn})
            ax.plot(d["n"], d["media"], marker=marcadores[cen], ms=4, lw=1,
                    ls="-" if alg == "insertion" else "--", color=CORES[alg],
                    label=f"{NOME_ALG[alg]}, {NOME_CEN[cen]} ($k$={k:.2f})".replace(".", ","))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Tamanho da entrada ($n$, escala log)")
    ax.set_ylabel("Tempo médio (s, escala log)")
    ax.set_title("Crescimento do tempo em escala log-log ($T \\propto n^k$)")
    ax.grid(which="major", alpha=0.3)
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURAS / "loglog.pdf")
    plt.close(fig)

    ex = pd.DataFrame(linhas_csv)
    ex.to_csv(DADOS / "expoentes.csv", index=False)
    teoria = {("insertion", "melhor"): "1 ($\\Theta(n)$)",
              ("insertion", "medio"): "2 ($\\Theta(n^2)$)",
              ("insertion", "pior"): "2 ($\\Theta(n^2)$)"}
    linhas = [
        r"\begin{tabular}{l l S[table-format=1.3] l}",
        r"\toprule",
        r"Algoritmo & Cenário & {Expoente $k$} & Expoente esperado \\",
        r"\midrule",
    ]
    for _, l in ex.iterrows():
        esperado = teoria.get((l["algoritmo"], l["cenario"]),
                              rf"$\approx {l['esperado_nlogn']:.2f}$ ($\Theta(n \log n)$)".replace(".", "{,}"))
        linhas.append(f"{NOME_ALG[l['algoritmo']]} & {NOME_CEN[l['cenario']].capitalize()} & "
                      f"{l['expoente']:.3f} & {esperado} \\\\")
    linhas += [r"\bottomrule", r"\end{tabular}"]
    salvar_tabela("expoentes.tex", linhas)


# ---------- Main ----------
def main():
    for pasta in (FIGURAS, TABELAS, DADOS):
        pasta.mkdir(parents=True, exist_ok=True)

    df = analise.carregar()
    r = analise.estatisticas(df)
    r.to_csv(DADOS / "estatisticas.csv", index=False)

    tabelas_estatisticas(r)
    for cen in CENARIOS:
        if cen in set(r["cenario"]):
            grafico_comparativo(r, cen)
            grafico_regressao(r, cen)
    comparacao(df, r)
    razao_dobro(r)
    regressoes(r)
    expoentes(r)
    print(f"Recursos gerados em: {RECURSOS}")


if __name__ == "__main__":
    main()
