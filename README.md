# Cloud Trader — Bootstrap Scaffold (v2)

What you get:
- **backlog/issues.csv** — GitHub-importable backlog (Issues → Import)
- **infra/** — Terraform skeleton (AWS VPC, S3 bucket with versioning, GPU VM, inference VM, IAM)
- **docker/** — Dockerfiles for training, inference, executor + MLflow docker-compose
- **.github/workflows/ci.yml** — basic CI (lint/tests + image builds)
- **src/** — stubs for data → features → training → inference → executor
- **src/orchestration/** — Prefect flow skeletons for daily ingest and nightly train+backtest
- **docs/** — goals, 2-part workflow, overlap matrix, overlap checklist
- **docker-compose.local.yml** — run inference+executor locally for smoke tests
