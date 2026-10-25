# Testing (BDD / TDD)

This monorepo uses a **test pyramid**:

```
        ╱╲
       ╱  ╲         Cucumber.js + Playwright  (acceptance / E2E)
      ╱────╲
     ╱      ╲       FastAPI route / agent tests (API)
    ╱────────╲
   ╱          ╲     pytest unit tests (tools, scoring, schemas)
  ╱────────────╲
```

| Layer | Tooling | Location | Default network |
| --- | --- | --- | --- |
| Unit | pytest | `apps/api/tests/` | Mocked HTTP / no Gemini |
| API | pytest + TestClient | `apps/api/tests/` | Mocked |
| Acceptance | Cucumber.js + Playwright | `tests/e2e/` | **`AGENT_MOCK=1`** fixtures |

Pytest stays the fast inner loop. Cucumber scenarios are the **primary acceptance layer** you can narrate in AI Engineer interviews: Given/When/Then maps to real user journeys.

## Red → Green → Refactor (TDD demo)

Example: add a guardrail that the agent stops at max steps.

1. **Red** — write a failing scenario first:

```gherkin
@agent
Scenario: Agent stops at max steps
  When I set the agent goal to include "[max_steps]"
  And I run the job search agent
  Then the agent message should mention max steps
```

2. Implement the missing step definition (it will fail if the UI/API do not emit that message).
3. **Green** — implement `AGENT_MOCK` branch + product behavior until the scenario passes.
4. **Refactor** — keep fixtures/scripted tool sequences readable; do not weaken assertions.

Repeat for new journeys: scenario → failing step → smallest product change → green → tidy up.

## Mock mode (`AGENT_MOCK=1`) + auth bypass

Acceptance tests must **not** hit real Gemini or live Himalayas/Jobicy feeds by default.

Set `AGENT_MOCK=1` on the API. The agent then:

- Uses fixture jobs (Himalayas + Jobicy attribution + real-looking apply URLs)
- Emits a scripted tool-call sequence (`search_jobs` → `score_fit` → `draft_cover_letter` → `save_to_tracker`)
- Supports scenario markers in the goal text:
  - `[max_steps]` — exhaust `AGENT_MAX_STEPS` and stop
  - `[source_failure]` — graceful “sources unavailable” message
  - `[timeout]` — graceful timeout message

Optional `@live` tag (excluded by default) can target a deployed `BASE_URL`.

Auth is required at AAL2 in production. For Cucumber, the orchestrator also sets
`AUTH_BYPASS=1` + `NEXT_PUBLIC_AUTH_BYPASS=1` (never on Vercel Production). The
cookie / `/api/e2e/session` seam switches roles (`admin` / `client` / `anonymous`).
See `features/access_control.feature`.

## How to run

### Unit / API (pytest)

```bash
cd apps/api
uv sync --group dev
uv run pytest -q
uv run ruff check .
```

### Web typecheck + build

```bash
cd apps/web
npm ci
npm run typecheck && npm run build
```

### Acceptance (Cucumber + Playwright)

From the repo root (starts API + Next in mock mode, then Cucumber):

```bash
cd apps/web && npm ci
cd ../api && uv sync --group dev
cd ../../tests/e2e && npm ci   # installs Chromium via postinstall
cd ../..
npm run test:e2e
```

Useful variants:

```bash
npm run test:e2e:smoke          # --tags '@smoke'
npm run test:e2e -- --tags '@tracker'
# Against already-running servers:
cd tests/e2e && BASE_URL=http://127.0.0.1:3000 npm test
# Live deploy (opt-in):
cd tests/e2e && BASE_URL=https://your-web.vercel.app npx cucumber-js --config cucumber.mjs --tags '@live'
```

### Tags

| Tag | Meaning |
| --- | --- |
| `@smoke` | Fast happy-path journeys |
| `@agent` | Agent / SSE / guardrail flows |
| `@tracker` | Tracker kanban status moves |
| `@live` | Real deployed URLs (excluded by default in `cucumber.mjs`) |

### Reports

After a run:

- HTML: `tests/e2e/reports/cucumber-report.html`
- JSON: `tests/e2e/reports/cucumber-report.json`
- Failure screenshots: `tests/e2e/reports/screenshots/`

## Interview talking points

- **Why Gherkin?** Shared language for product behavior; scenarios double as demo scripts.
- **Why keep pytest?** Pyramid — unit tests catch scoring/tool regressions in milliseconds.
- **Why API mock mode over route interception?** Exercises the full stack (Next ↔ FastAPI ↔ SSE ↔ UI) while remaining deterministic.
- **Guardrails as features** — max steps, source failure, timeout are acceptance criteria, not afterthoughts.
