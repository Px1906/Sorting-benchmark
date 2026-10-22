#include <stdlib.h>
#include "sorts.h"

void insertion_sort(int v[], int n) {
    for (int i = 1; i < n; i++) {
        int chave = v[i];
        int j = i - 1;
        while (j >= 0 && v[j] > chave) {
            v[j + 1] = v[j];
            j--;
        }
        v[j + 1] = chave;
    }
}

static void merge(int v[], int p, int q, int r) {
    int n1 = q - p + 1;
    int n2 = r - q;

    int *L = malloc(n1 * sizeof(int));
    int *R = malloc(n2 * sizeof(int));

    for (int i = 0; i < n1; i++) L[i] = v[p + i];
    for (int j = 0; j < n2; j++) R[j] = v[q + 1 + j];

    int i = 0, j = 0, k = p;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) v[k++] = L[i++];
        else              v[k++] = R[j++];
    }
    while (i < n1) v[k++] = L[i++];
    while (j < n2) v[k++] = R[j++];

    free(L);
    free(R);
}

void merge_sort(int v[], int p, int r) {
    if (p >= r) return;
    int q = p + (r - p) / 2;
    merge_sort(v, p, q);
    merge_sort(v, q + 1, r);
    merge(v, p, q, r);
}

void merge_sort_wrapper(int v[], int n) {
    merge_sort(v, 0, n - 1);
}