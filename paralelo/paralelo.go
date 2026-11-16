package main

import (
	"fmt"
	"os"
)

type Comm interface {
	Send(data interface{}, dest int, tag int) int
	Recv(data interface{}, source int, tag int) int
	Barrier()
	GetRank() int
	GetSize() int
}

const (
	tagB = iota + 1
	tagA
	tagC
	tagTempo
	tagHost
)

const pedaco = 1 << 20

func envia(w Comm, buf []float64, dest, tag int) {
	for off := 0; off < len(buf); off += pedaco {
		fim := min(off+pedaco, len(buf))
		w.Send(buf[off:fim], dest, tag)
	}
}

func recebe(w Comm, buf []float64, src, tag int) {
	for off := 0; off < len(buf); off += pedaco {
		fim := min(off+pedaco, len(buf))
		w.Recv(buf[off:fim], src, tag)
	}
}

func particao(n, p int) (linhas, inicio []int) {
	linhas = make([]int, p)
	inicio = make([]int, p)
	base, resto := n/p, n%p
	pos := 0
	for r := 0; r < p; r++ {
		linhas[r] = base
		if r < resto {
			linhas[r]++
		}
		inicio[r] = pos
		pos += linhas[r]
	}
	return
}

func broadcastArvore(w Comm, B []float64, rank, p int) {
	for mask := 1; mask < p; mask <<= 1 {
		if rank < mask {
			if dest := rank + mask; dest < p {
				envia(w, B, dest, tagB)
			}
		} else if rank < 2*mask {
			recebe(w, B, rank-mask, tagB)
		}
	}
}

func executa(w Comm, n int, wtime func() float64) {
	rank, p := w.GetRank(), w.GetSize()
	linhas, inicio := particao(n, p)
	minhas := linhas[rank]

	var A, B, C []float64

	w.Barrier()
	t0 := wtime()
	if rank == 0 {
		A, B = geraMatrizes(n)
		C = make([]float64, n*n)
	}
	w.Barrier()
	t1 := wtime()

	var aLocal, cLocal []float64
	if rank == 0 {
		aLocal = A[:minhas*n]
		cLocal = C[:minhas*n]
	} else {
		B = make([]float64, n*n)
		aLocal = make([]float64, minhas*n)
		cLocal = make([]float64, minhas*n)
	}
	broadcastArvore(w, B, rank, p)
	if rank == 0 {
		for r := 1; r < p; r++ {
			envia(w, A[inicio[r]*n:(inicio[r]+linhas[r])*n], r, tagA)
		}
	} else {
		recebe(w, aLocal, 0, tagA)
	}
	w.Barrier()
	t2 := wtime()

	tc0 := wtime()
	multiplica(aLocal, B, cLocal, n)
	tCalc := wtime() - tc0
	w.Barrier()
	t3 := wtime()

	if rank == 0 {
		for r := 1; r < p; r++ {
			recebe(w, C[inicio[r]*n:(inicio[r]+linhas[r])*n], r, tagC)
		}
	} else {
		envia(w, cLocal, 0, tagC)
	}
	w.Barrier()
	t4 := wtime()

	host, _ := os.Hostname()
	if rank != 0 {
		w.Send([]float64{tCalc}, 0, tagTempo)
		w.Send(host, 0, tagHost)
		return
	}

	fmt.Printf("Paralelo: N=%d, processos=%d\n", n, p)
	fmt.Printf("Tempo de geração:       %.3f s\n", t1-t0)
	fmt.Printf("Tempo de distribuição:  %.3f s\n", t2-t1)
	fmt.Printf("Tempo de cálculo:       %.3f s\n", t3-t2)
	fmt.Printf("Tempo de coleta:        %.3f s\n", t4-t3)
	fmt.Printf("Tempo total:            %.3f s\n", t4-t0)
	fmt.Printf("FASES geracao=%.3f distribuicao=%.3f calculo=%.3f coleta=%.3f total=%.3f\n",
		t1-t0, t2-t1, t3-t2, t4-t3, t4-t0)
	fmt.Printf("PROCESSO rank=0 host=%s linhas=%d calculo=%.3f\n", host, minhas, tCalc)
	for r := 1; r < p; r++ {
		tc := make([]float64, 1)
		w.Recv(tc, r, tagTempo)
		var h string
		w.Recv(&h, r, tagHost)
		fmt.Printf("PROCESSO rank=%d host=%s linhas=%d calculo=%.3f\n", r, h, linhas[r], tc[0])
	}
	verifica(C, n)
}
