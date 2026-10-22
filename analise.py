from pathlib import Path
 
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
 
# ====================== CONFIGURAÇÃO (edite aqui) ======================
AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
SAIDA = AQUI / "saida"
SAIDA.mkdir(exist_ok=True)
 
ALGORITMOS = ["insertion", "merge"]
CENARIOS = ["melhor", "medio", "pior"]
CORES = {"insertion": "tab:red", "merge": "tab:blue"}
REPS_ESPERADAS = 50
 
# O que gerar (True = gera, False = pula)
GERAR_TABELAS = True
GERAR_GRAFICOS_COMPARATIVOS = True     # os 3 gráficos exigidos (um por cenário)
GERAR_GRAFICOS_INDIVIDUAIS = True      # gráficos de um algoritmo em um cenário
GERAR_RAZAO_DOBRO = True
GERAR_REGRESSAO = True
 
# Tabelas individuais a salvar: (algoritmo, cenario). Comente a linha para pular.
TABELAS = [
    ("insertion", "melhor"),
    ("insertion", "medio"),
    ("insertion", "pior"),
    ("merge", "melhor"),
    ("merge", "medio"),
    ("merge", "pior"),
]
 
# Gráficos individuais: (algoritmo, cenario). Deixe a lista vazia [] para nenhum.
GRAFICOS_INDIVIDUAIS = [
    ("insertion", "melhor"),
]
ESCALA_LOG_INDIVIDUAL = False          # True = eixo y logarítmico nos individuais
 
GRAUS_REGRESSAO = (1, 2, 3)
# =======================================================================
 
COLUNAS_TABELA = ["n", "media", "desvio", "ic95", "minimo", "maximo", "reps"]
 
 
# ---------- 1. Carregar ----------
def carregar():
    """Lê os CSVs que existirem e junta tudo (uma linha por execução)."""
    partes = []
    for cen in CENARIOS:
        arquivos = sorted(RESULTADOS.glob(f"*/{cen}/*.csv"))
        if arquivos:
            partes.extend(pd.read_csv(caminho) for caminho in arquivos)
        else:
            print(f"[aviso] nenhum arquivo do cenário '{cen}' em resultados/, cenário ignorado.")
    if not partes:
        raise SystemExit("Nenhum CSV encontrado em resultados/. Rode ./main antes.")
 
    df = pd.concat(partes, ignore_index=True)
    df["algoritmo"] = df["algoritmo"].str.strip().str.lower()
    df["cenario"] = df["cenario"].str.strip().str.lower()

    numericas = ["n", "repeticao", "tempo_s"]
    for col in numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    invalidas = df[df[numericas].isna().any(axis=1)]
    if len(invalidas) > 0:
        print(f"[ATENÇÃO] {len(invalidas)} linha(s) inválida(s) removida(s):")
        print(invalidas.to_string())
        df = df.drop(invalidas.index)
    df["n"] = df["n"].astype(int)
 
    contagem = df.groupby(["algoritmo", "cenario", "n"]).size()
    problemas = contagem[contagem != REPS_ESPERADAS]
    if len(problemas) > 0:
        print(f"[ATENÇÃO] grupos sem {REPS_ESPERADAS} repetições:")
        print(problemas.to_string())
    return df
 
 
# ---------- 2. Estatísticas ----------
def estatisticas(df):
    """Uma linha por (algoritmo, cenario, n): média, desvio, mín, máx e IC 95%."""
    g = df.groupby(["algoritmo", "cenario", "n"])["tempo_s"]
    r = g.agg(media="mean", desvio="std", minimo="min",
              maximo="max", reps="count").reset_index()
    t = stats.t.ppf(0.975, r["reps"] - 1)          # t de Student, 95% bilateral
    r["ic95"] = t * r["desvio"] / np.sqrt(r["reps"])
    return r
 
 
def dados(r, alg, cen):
    """Linhas de UM algoritmo em UM cenário, ordenadas por n."""
    return r[(r["algoritmo"] == alg) & (r["cenario"] == cen)].sort_values("n")
 
 
# ---------- 3. Tabelas ----------
def salvar_tabelas(r):
    for alg, cen in TABELAS:
        d = dados(r, alg, cen)
        if d.empty:
            continue                                # cenário ainda sem dados
        d[COLUNAS_TABELA].to_csv(SAIDA / f"tabela_{alg}_{cen}.csv", index=False)
 
 
# ---------- 4. Gráficos ----------
def grafico_comparativo(r, cen):
    """Barras agrupadas (uma cor por algoritmo) com barras de erro de IC 95%."""
    d = r[r["cenario"] == cen]
    ns = sorted(d["n"].unique())
    x = np.arange(len(ns))
    larg = 0.38
 
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, alg in enumerate(ALGORITMOS):
        s = d[d["algoritmo"] == alg].set_index("n").reindex(ns)
        ax.bar(x + (i - 0.5) * larg, s["media"], larg, yerr=s["ic95"],
               capsize=3, label=alg, color=CORES[alg])
    ax.set_xticks(x)
    ax.set_xticklabels(ns, rotation=45)
    ax.set_yscale("log")                 # os tempos variam várias ordens de grandeza
    ax.set_xlabel("Tamanho da entrada (n)")
    ax.set_ylabel("Tempo médio de execução (s, escala log)")
    ax.set_title(f"Tempo médio por algoritmo, caso {cen}")
    ax.legend(title="Algoritmo")
    fig.tight_layout()
    fig.savefig(SAIDA / f"grafico_{cen}.png", dpi=200)
    plt.close(fig)
 
 
def grafico_individual(r, alg, cen, log=False):
    """Barras de UM algoritmo em UM cenário, com IC 95%."""
    d = dados(r, alg, cen)
    if d.empty:
        return
    ns = list(d["n"])
    x = np.arange(len(ns))
 
    # unidade escolhida pelo maior valor, para os números ficarem legíveis
    maximo = d["media"].max()
    if maximo < 1e-3:
        fator, unidade = 1e6, "µs"
    elif maximo < 1:
        fator, unidade = 1e3, "ms"
    else:
        fator, unidade = 1, "s"
 
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x, d["media"] * fator, 0.6, yerr=d["ic95"] * fator,
           capsize=3, color=CORES[alg], label=f"{alg} (média ± IC 95%)")
    ax.set_xticks(x)
    ax.set_xticklabels(ns, rotation=45)
    if log:
        ax.set_yscale("log")
    escala = "escala log" if log else "escala linear"
    ax.set_xlabel("Tamanho da entrada (n)")
    ax.set_ylabel(f"Tempo médio de execução ({unidade}, {escala})")
    ax.set_title(f"{alg.capitalize()} Sort, caso {cen}")
    ax.legend(title="Algoritmo")
    fig.tight_layout()
    sufixo = "_log" if log else ""
    fig.savefig(SAIDA / f"grafico_{alg}_{cen}{sufixo}.png", dpi=200)
    plt.close(fig)
 
 
# ---------- 5. Razão ao dobrar n ----------
def razao_dobro(r):
    """T(2n)/T(n) para os pares em que 2n existe nos dados. Não filtra nada."""
    linhas = []
    for (alg, cen), d in r.groupby(["algoritmo", "cenario"]):
        m = d.set_index("n")["media"]
        for n in m.index:
            if 2 * n in m.index:
                linhas.append({"algoritmo": alg, "cenario": cen, "n": n,
                               "2n": 2 * n, "razao": m[2 * n] / m[n]})
    pd.DataFrame(linhas).to_csv(SAIDA / "razao_dobro.csv", index=False)
 
 
# ---------- 6. Regressão polinomial ----------
def regressao(r, alg, cen, grau):
    """Ajusta polinômio de grau 'grau' às médias. x = n / 1e6 (evita mal condicionamento)."""
    d = dados(r, alg, cen)
    x = d["n"].to_numpy(float) / 1e6
    y = d["media"].to_numpy(float)
    coef = np.polyfit(x, y, grau)
    pred = np.polyval(coef, x)
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    return coef, r2
 
 
def texto_funcao(coef):
    """Monta 'T(x) = 3.1·x^2 + 0.2·x + 0.001' (x = n em milhões)."""
    grau = len(coef) - 1
    termos = []
    for i, c in enumerate(coef):
        p = grau - i
        if p == 0:
            termos.append(f"{c:.4g}")
        elif p == 1:
            termos.append(f"{c:.4g}·x")
        else:
            termos.append(f"{c:.4g}·x^{p}")
    return "T(x) = " + " + ".join(termos)
 
 
def salvar_regressoes(r):
    linhas = []
    for alg in ALGORITMOS:
        for cen in CENARIOS:
            if dados(r, alg, cen).empty:
                continue
            for g in GRAUS_REGRESSAO:
                coef, r2 = regressao(r, alg, cen, g)
                linhas.append({"algoritmo": alg, "cenario": cen, "grau": g,
                               "funcao (x = n/1e6)": texto_funcao(coef),
                               "R2": round(r2, 6)})
    pd.DataFrame(linhas).to_csv(SAIDA / "regressoes.csv", index=False)
 
 
# ---------- Main ----------
def main():
    df = carregar()
    r = estatisticas(df)
    cenarios_com_dados = [c for c in CENARIOS if c in set(r["cenario"])]
 
    r.to_csv(SAIDA / "estatisticas_completas.csv", index=False)
 
    if GERAR_TABELAS:
        salvar_tabelas(r)
    if GERAR_GRAFICOS_COMPARATIVOS:
        for cen in cenarios_com_dados:
            grafico_comparativo(r, cen)
    if GERAR_GRAFICOS_INDIVIDUAIS:
        for alg, cen in GRAFICOS_INDIVIDUAIS:
            grafico_individual(r, alg, cen, log=ESCALA_LOG_INDIVIDUAL)
    if GERAR_RAZAO_DOBRO:
        razao_dobro(r)
    if GERAR_REGRESSAO:
        salvar_regressoes(r)
 
    print(f"Pronto. Arquivos gerados em: {SAIDA}")
 
 
if __name__ == "__main__":
    main()