# Sorting Benchmark

Comparação experimental do tempo de execução do **Insertion Sort** e do **Merge Sort** em C, com análise estatística e gráficos em Python.

## Cenários

| Cenário  | Entrada                          |
|----------|----------------------------------|
| `melhor` | vetor crescente (1, 2, ..., n)   |
| `medio`  | vetor aleatório (`rand()`)       |
| `pior`   | vetor decrescente (n, ..., 2, 1) |

Tamanhos testados: 1.000, 2.000, 5.000, 10.000, 20.000, 50.000, 100.000, 200.000, 500.000 e 1.000.000 elementos, com 50 repetições cada.

## Estrutura

```
.
├── main.c            # benchmark: gera as entradas, mede os tempos e grava os CSVs
├── sorts.c / sorts.h # implementações do Insertion Sort e do Merge Sort
├── analise.py        # estatísticas, tabelas, gráficos e regressões
├── Makefile
├── requirements.txt  # dependências do Python
├── docs/             # relatório (LaTeX/abnTeX2): relatorio.tex, referencias.bib,
│                     # gerar_recursos.py e recursos/ (figuras e tabelas geradas)
├── resultados/       # CSVs brutos gerados pelo ./main (não versionado)
└── saida/            # tabelas e gráficos gerados pelo analise.py (não versionado)
```

## Como executar

### 1. Benchmark (C)

```bash
make        # compila
./main      # grava um CSV por algoritmo, cenário e tamanho em resultados/
```

Rode o `./main` (ou `make run`) a partir da raiz do repositório. Com tudo selecionado são 60 arquivos (2 algoritmos × 3 cenários × 10 tamanhos), organizados em `resultados/<algoritmo>/<cenario>/<n>.csv`, com `n` em 7 dígitos (por exemplo, `resultados/insertion/melhor/0001000.csv`). Cada arquivo tem um cabeçalho e uma linha por repetição, no formato `algoritmo,cenario,n,repeticao,tempo_s`.

Os algoritmos, cenários e tamanhos a rodar, e o número de repetições, ficam no bloco de configuração no topo do `main.c`.

### 2. Análise (Python)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python analise.py
```

Os resultados são gravados na pasta `saida/`:

- `estatisticas_completas.csv`: média, desvio padrão, mínimo, máximo e IC 95% por algoritmo, cenário e n
- `tabela_<algoritmo>_<cenario>.csv`: tabela individual de cada combinação
- `grafico_<cenario>.png`: comparação entre os dois algoritmos em cada cenário
- `razao_dobro.csv`: razão T(2n)/T(n)
- `regressoes.csv`: ajuste polinomial (graus 1, 2 e 3) com R²

As opções da análise (quais tabelas e gráficos gerar) ficam no bloco de configuração no topo do `analise.py`.

### 3. Relatório (LaTeX)

```bash
venv/bin/python docs/gerar_recursos.py   # figuras e tabelas em docs/recursos/
cd docs && latexmk -pdf relatorio.tex    # gera docs/relatorio.pdf
```

Requer TeX Live com abnTeX2 (`texlive-publishers`). Sempre que novos CSVs forem gerados, rode o `gerar_recursos.py` de novo antes de compilar.
