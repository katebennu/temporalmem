# Tasks: add-inspector-ui

## 1. Build

- [x] 1.1 `MemoryAgent.answer_traced()` — answer + ordered tool trace; `answer()` delegates
- [x] 1.2 Streamlit app with Ask / Search / Timeline / Runs tabs (`ui` dependency group)
- [x] 1.3 Timeline: per-entity validity bars via plotly, superseded facts table
- [x] 1.4 Runs: per-type accuracy grouped bars across results files + failure browser
- [x] 1.5 Smoke test: headless server responds, script executes all tabs against live graph

## 2. Polish (as needed)

- [ ] 2.1 Screenshot pass in a real browser (label collisions, overflow) — validator covers color, not layout
- [ ] 2.2 Ask view: stream progress instead of a single spinner (answer takes ~30–60s)
- [ ] 2.3 Dark mode styling (current chart chrome is light-surface only)
