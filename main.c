#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include "sorts.h"

#define QTD(v) (int)(sizeof(v) / sizeof((v)[0]))

// ====================== CONFIGURAÇÃO ======================

const char *algoritmos[] = {"insertion", "merge"};
void (*funcoes[])(int[], int) = {insertion_sort, merge_sort_wrapper};

const char *cenarios[] = {"melhor", "medio", "pior"};

const int tamanhos_vetor[] = {1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000};

#define REPETICOES 50

// algoritmos: 0 = insertion, 1 = merge
const int algoritmos_a_rodar[] = {0, 1};

// cenarios:   0 = melhor, 1 = medio, 2 = pior
const int cenarios_a_rodar[] = {2};

// tamanhos:   0 = 1000,   1 = 2000,   2 = 5000,   3 = 10000,  4 = 20000,
//             5 = 50000,  6 = 100000, 7 = 200000, 8 = 500000, 9 = 1000000
const int tamanhos_a_rodar[] = {9};
// =======================================================================

double medir(void (*funcao) (int[], int), int v[], int n) {
    struct timespec inicio, fim;
    clock_gettime(CLOCK_MONOTONIC, &inicio);
    funcao(v,n);
    clock_gettime(CLOCK_MONOTONIC, &fim);
    return (fim.tv_sec - inicio.tv_sec) + (fim.tv_nsec - inicio.tv_nsec)/1e9;
}

void preencher_aleatorio(int *v, int n) {
    for (int k = 0; k < n; k++) {
        v[k] = rand();
    }
}

// Melhor caso: 1, 2, 3, ..., n
void preencher_crescente(int *v, int n) {
    for (int k = 0; k < n; k++) {
        v[k] = k + 1;
    }
}

// Pior caso: n, n-1, ..., 1
void preencher_decrescente(int *v, int n) {
    for (int k = 0; k < n; k++) {
        v[k] = n - k;
    }
}

// Preenche o vetor de acordo com o cenário (0 = melhor, 1 = medio, 2 = pior)
void preencher(int c, int *v, int n) {
    switch (c) {
    case 0:
        preencher_crescente(v, n);
        break;
    case 1:
        preencher_aleatorio(v, n);
        break;
    case 2:
        preencher_decrescente(v, n);
        break;
    default:
        break;
    }
}

int main() {
    mkdir("resultados", 0755);

    for (int ic = 0; ic < QTD(cenarios_a_rodar); ic++) {
        int c = cenarios_a_rodar[ic];
        for (int it = 0; it < QTD(tamanhos_a_rodar); it++) {
            int i = tamanhos_a_rodar[it];
            int *aux = malloc(tamanhos_vetor[i] * sizeof(int));
            for (int ia = 0; ia < QTD(algoritmos_a_rodar); ia++) {
                int a = algoritmos_a_rodar[ia];
                // resultados/<algoritmo>/<cenario>/<n>.csv (mkdir cria um nível por vez)
                char pasta[96], nome[128];
                snprintf(pasta, sizeof(pasta), "resultados/%s", algoritmos[a]);
                mkdir(pasta, 0755);
                snprintf(pasta, sizeof(pasta), "resultados/%s/%s", algoritmos[a], cenarios[c]);
                mkdir(pasta, 0755);
                snprintf(nome, sizeof(nome), "%s/%07d.csv", pasta, tamanhos_vetor[i]);
                FILE *arquivo = fopen(nome, "w");
                if (!arquivo) {
                    perror(nome);
                    continue;
                }
                fprintf(arquivo, "algoritmo,cenario,n,repeticao,tempo_s\n");

                for (int j = 0; j < REPETICOES; j++) {
                    srand(j + 1);   // mesma entrada aleatória para os dois algoritmos
                    preencher(c, aux, tamanhos_vetor[i]);
                    double tempo = medir(funcoes[a], aux, tamanhos_vetor[i]);
                    fprintf(arquivo, "%s,%s,%d,%d,%.9f\n", algoritmos[a], cenarios[c], tamanhos_vetor[i], j + 1, tempo);
                    fflush(arquivo);
                }
                fclose(arquivo);
            }
            free(aux);
        }
    }
    return 0;
}