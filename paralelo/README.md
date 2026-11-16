# T2: versão paralela (Go + MPI)

Multiplicação C = A × B (N = 5000 por padrão) com `github.com/mvneves/gompi`.

## Compilar (no cluster Atlântica, frontend)
```bash
source ~/lad-go-mpi/setup.sh      # Go 1.23.2 + Open MPI 4.1.1 (a cada login)
cd paralelo
go mod tidy                       # baixa gompi e gera go.sum
go build -o paralelo .
```

## Executar
```bash
mpirun -np 8 ./paralelo -n 500    # teste pequeno (apenas em job interativo, nada é medido)
```
As medições são feitas só por `sbatch` (ver `../jobs/`).

## Saída
`Tempo de geração/distribuição/cálculo/coleta/total`, uma linha `FASES ...`, uma linha `PROCESSO rank=.. host=.. linhas=.. calculo=..` por processo e a verificação do sequencial (cantos de C e checksum).
