# Comparação de Tecnologias de Invocação de Serviços Remotos

Trabalho da disciplina **Computação Distribuída** (Prof. Nabor C. Mendonça) comparando **SOAP, REST, GraphQL e gRPC** por meio da especificação, implementação e avaliação de desempenho (testes de carga) de um **Serviço de Streaming de Músicas** em **duas linguagens de programação diferentes** (**Python 3.12** e **Node.js 22 / TypeScript**), totalizando **8 implementações** conectadas a um banco **PostgreSQL 16** via Docker.

---

## Arquitetura do Projeto

Todas as 8 implementações compartilham:
- O mesmo banco de dados **PostgreSQL 16** (`db/init.sql`) com schema normalizado (`users`, `songs`, `playlists`, `playlist_songs`), **6–7 atributos por entidade** e dataset determinístico em escala (**500 usuários**, **1.000 músicas**, **1.000 playlists**, ~10.000 associações).
- Os mesmos contratos formais em `contracts/`:
  - `contracts/music_streaming.wsdl` (WSDL 1.1 compartilhado entre Python SOAP e Node.js SOAP)
  - `contracts/schema.graphql` (Schema SDL compartilhado entre Python GraphQL e Node.js GraphQL)
  - `contracts/music_streaming.proto` (Protobuf v3 compartilhado entre Python gRPC e Node.js gRPC)
- Os mesmos limites de recursos no Docker Compose (`1.0 vCPU`, `512 MB RAM`, pool PostgreSQL `max=20`), garantindo comparação justa nos testes de carga.

### Mapa das 8 Implementações

| # | Linguagem | Tecnologia | Framework / Biblioteca | Porta | Endpoint Principal |
|---|---|---|---|---|---|
| 1 | Python 3.12 | **REST** | FastAPI + Uvicorn + asyncpg | `8001` | `http://localhost:8001/docs` |
| 2 | Python 3.12 | **SOAP** | FastAPI + lxml + WSDL 1.1 | `8002` | `http://localhost:8002/soap?wsdl` |
| 3 | Python 3.12 | **GraphQL** | Strawberry GraphQL + FastAPI | `8003` | `http://localhost:8003/graphql` |
| 4 | Python 3.12 | **gRPC** | `grpcio` (`grpc.aio`) + Protobuf | `50051` | `localhost:50051` |
| 5 | Node.js 22 (TS) | **REST** | Fastify + `pg` | `8101` | `http://localhost:8101/songs` |
| 6 | Node.js 22 (TS) | **SOAP** | `soap` (`node-soap`) + WSDL 1.1 | `8102` | `http://localhost:8102/soap?wsdl` |
| 7 | Node.js 22 (TS) | **GraphQL** | Apollo Server 4 + `pg` | `8103` | `http://localhost:8103/` |
| 8 | Node.js 22 (TS) | **gRPC** | `@grpc/grpc-js` + `@grpc/proto-loader` | `50052` | `localhost:50052` |

---

## Estrutura de Pastas

```text
trabalhodistribuidaseis/
├── docker-compose.yml              # Orquestração: Postgres + 8 serviços + Runner
├── db/
│   └── init.sql                    # Schema PostgreSQL + Seed determinístico
├── contracts/
│   ├── music_streaming.wsdl        # Contrato SOAP 1.1 / WSDL 1.1
│   ├── schema.graphql              # Contrato GraphQL SDL
│   └── music_streaming.proto       # Contrato gRPC / Protobuf v3
├── services/
│   ├── python/                     # 4 APIs em Python 3.12
│   │   ├── common/db.py            # Camada SQL asyncpg compartilhada
│   │   └── apis/
│   │       ├── rest_app.py
│   │       ├── soap_app.py
│   │       ├── graphql_app.py
│   │       └── grpc_server.py
│   └── node/                       # 4 APIs em Node.js 22 + TypeScript
│       └── src/
│           ├── common/db.ts        # Camada SQL pg compartilhada
│           ├── rest/server.ts
│           ├── soap/server.ts
│           ├── graphql/server.ts
│           └── grpc/server.ts
├── benchmark/
│   ├── smoke_test.py               # Validação funcional (CRUD + 5 consultas + bordas) nas 8 APIs
│   ├── load_test.py                # Suite de testes de carga (W1: 50/200/400 VUs; W2/W3: 100 VUs)
│   └── stress_test.py              # Teste de estresse até o limite (rampa 10 → 1000 VUs)
├── analysis/
│   └── generate_charts.py          # Gera 7 gráficos PNG (300 DPI)
├── results/
│   ├── benchmark_results.json      # Dados brutos completos dos testes de carga
│   ├── benchmark_summary.csv       # Tabela resumo importável em planilhas
│   ├── stress_results.json         # Dados brutos do teste de estresse até o limite
│   ├── stress_summary.csv          # Tabela resumo do teste de estresse
│   └── charts/                     # 7 gráficos PNG prontos
```

---

## Como Executar (Reproduzir Tudo com Docker)

Pré-requisito único: **Docker Desktop** (ou Docker Engine + Docker Compose v2).

```bash
# 1. Construir as imagens e subir PostgreSQL + todos os 8 serviços
docker compose --profile tools build
docker compose up -d

# 2. Validar funcionalmente as 8 implementações (5 consultas obrigatórias + CRUD completo)
docker compose --profile tools run --rm runner python benchmark/smoke_test.py

# 3. Executar toda a bateria de testes de carga (40 cenários × 2 repetições, até 400 VUs)
docker compose --profile tools run --rm runner python benchmark/load_test.py --duration 3 --warmup 1 --runs 2

# 3b. Executar o teste de estresse até o limite (rampa 10 → 1000 VUs / pontos de ruptura)
docker compose --profile tools run --rm runner python benchmark/stress_test.py --duration 3

# 4. Gerar os 7 gráficos em alta resolução (results/charts/)
docker compose --profile tools run --rm runner python analysis/generate_charts.py

# 5. Encerrar todos os containers quando terminar
docker compose down -v
```
