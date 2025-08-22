# Overlap Checklist
1. List all scripts and cron jobs in the current trader.
2. For each, mark: Data → Features → Signals → Orders → Reports.
3. Map to cloud equivalents in `src/*` and Prefect flows.
4. If a step overlaps, port the code into `src/common` and call it from both lanes until cutover.
5. Add gating tests/backtests before switching live traffic.
