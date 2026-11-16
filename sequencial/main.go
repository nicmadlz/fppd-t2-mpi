// Multiplicação de matrizes: versão sequencial (referência para o speedup).
//
// Uso: ./sequencial [-n 5000]
//
// As funções geraMatrizes, multiplica e verifica devem ser usadas na versão
// paralela SEM ALTERAÇÃO: as medições só são comparáveis se as duas versões
// usarem exatamente o mesmo código de geração e de cálculo.
package main

import (
	"flag"
	"fmt"
	"math/rand"
	"os"
	"time"
)

// Semente fixa: as duas versões geram as mesmas matrizes.
const semente = 42

func main() {
	n := flag.Int("n", 5000, "dimensão das matrizes")
	flag.Parse()

	host, _ := os.Hostname()
	fmt.Printf("Sequencial: N=%d, host=%s\n", *n, host)

	inicio := time.Now()

	A, B := geraMatrizes(*n)
	tGeracao := time.Since(inicio)

	C := make([]float64, (*n)*(*n))
	multiplica(A, B, C, *n)

	tTotal := time.Since(inicio)

	fmt.Printf("Tempo de geração:       %.3f s\n", tGeracao.Seconds())
	fmt.Printf("Tempo de multiplicação: %.3f s\n", (tTotal - tGeracao).Seconds())
	fmt.Printf("Tempo total:            %.3f s\n", tTotal.Seconds())
	verifica(C, *n)
}

// geraMatrizes devolve as matrizes A e B, de dimensão n×n, guardadas em
// slices unidimensionais linha a linha: o elemento [i][j] fica na posição i*n + j.
func geraMatrizes(n int) (A, B []float64) {
	rng := rand.New(rand.NewSource(semente))
	A = make([]float64, n*n)
	B = make([]float64, n*n)
	for i := range A {
		A[i] = rng.Float64()
	}
	for i := range B {
		B[i] = rng.Float64()
	}
	return A, B
}

// multiplica calcula C = A × B para um bloco de linhas de A.
// A e C têm o mesmo número de linhas (len(A)/n); B é a matriz n×n inteira.
//
// Os laços estão na ordem i-k-j: o laço interno percorre uma linha de B e
// uma linha de C, posições contíguas na memória, o que aproveita a cache.
func multiplica(A, B, C []float64, n int) {
	linhas := len(A) / n
	for i := 0; i < linhas; i++ {
		ci := C[i*n : (i+1)*n]
		for j := range ci {
			ci[j] = 0
		}
		for k := 0; k < n; k++ {
			a := A[i*n+k]
			bk := B[k*n : (k+1)*n]
			for j := range ci {
				ci[j] += a * bk[j]
			}
		}
	}
}

// verifica imprime os quatro cantos de C e a soma de todos os elementos.
// A saída deve ser idêntica nas versões sequencial e paralela.
func verifica(C []float64, n int) {
	fmt.Println("Verificação:")
	fmt.Printf("  C[0][0]     = %.15f\n", C[0])
	fmt.Printf("  C[0][N-1]   = %.15f\n", C[n-1])
	fmt.Printf("  C[N-1][0]   = %.15f\n", C[(n-1)*n])
	fmt.Printf("  C[N-1][N-1] = %.15f\n", C[(n-1)*n+n-1])
	soma := 0.0
	for _, v := range C {
		soma += v
	}
	fmt.Printf("  Checksum    = %.15f\n", soma)
}
