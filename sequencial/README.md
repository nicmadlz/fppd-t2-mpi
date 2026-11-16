# T2: versão sequencial

Compilar e executar no cluster, com o ambiente configurado como na aula 19:

```bash
go build -o sequencial .
./sequencial            # N = 5000
./sequencial -n 500     # matrizes menores, só para testes
```

As medições do trabalho usam N = 5000 e são feitas por job batch. O script `sequencial.job` mede a versão sequencial (10 repetições, nó exclusivo) e serve de modelo para os scripts da versão paralela:

```bash
sbatch sequencial.job
```
