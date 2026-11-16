package main

import (
	"flag"

	mpi "github.com/mvneves/gompi"
)

func main() {
	n := flag.Int("n", 5000, "dimensão das matrizes")
	flag.Parse()

	mpi.Init()
	defer mpi.Finalize()

	world := mpi.NewComm(true)
	executa(world, *n, mpi.WTime)
}
