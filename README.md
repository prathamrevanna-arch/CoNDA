# CoNDA
Adversarially evaluated runtime system for detecting, explaining, and challenging suspicious coordination among autonomous DeFi trading agents.
# CoNDA — Coordination Detection Analytics

A live dashboard that detects tacit collusion between autonomous trading agents in a simulated DeFi market. It streams a real-time Coordination Risk score (0–100) with per-signal evidence, compares observed prices against a competitive counterfactual, and opens contestable cases on a local blockchain.

Built for hackathon judges — clarity over feature count.

---

## Features

### 3D Currency Hero Animation
- Large, eye-catching CSS 3D animation on the Overview page
- Eight floating, spinning coin tokens (`$`, `ETH`, `BTC`, diamond symbols) with front/back faces and visible edges for real depth
- Parallax mouse-tracking that shifts the entire token stage
- Soft colored glow per token with pulsing animation
- Responsive scaling for tablet and mobile

### Multi-Page Navigation
- Collapsible sidebar (desktop) with icon-only collapsed mode and tooltips
- Mobile hamburger drawer with scrim overlay
- Four pages: Overview, Signal analysis, Cases & challenges, Methodology
- Active page highlighting with smooth transitions

### Overview Page
- 3D currency hero animation with headline and subtext
- Four key metric cards: current risk score, observed mid-price vs reference, open investigations, evidence compute time
- Live price chart (observed mid-price vs counterfactual reference)
- Animated risk gauge (0–100, color-banded: green < 40, amber 40–69, red >= 70)
- Agent activity table (agent ID, last price, PnL, pair risk, side)
- Signal breakdown preview with contribution bars and explanations
- Recent cases preview with status badges and challenge buttons

### Signal Analysis Page
- Window assessment panel with large risk score and evidence hash
- Full signal contribution breakdown with horizontal bars
- Each signal shows its value, contribution, and plain-language explanation
- Only renders signals that are present — missing keys are handled gracefully
- Full pricing context chart for the assessment window

### Cases & Challenges Page
- Case lifecycle stats: total, under review, challenged, cleared
- Full case registry with all four statuses: OPEN, CHALLENGED, CLEARED, ESCALATED
- Truncated transaction hashes for on-chain transparency
- "Submit Challenge" button that POSTs to `/case/{id}/challenge`
- Status language uses "under review", "cleared", "escalated" — never "guilty"
- Challenge result label is "policy compliance verified"

### Methodology Page
- Three-step explanation: competitive counterfactual, behavioral signals, contestable cases
- Interpretation note clarifying the score is analytical, not a finding of wrongdoing

### Price Chart (Recharts)
- Observed mid-price vs counterfactual reference price over time
- Vertical dashed markers at shock ticks
- Handles up to 600 data points without lag
- Clear legend, tooltips, and formatted axes

### Risk Gauge
- 0–100 scale with color bands (green / amber / red)
- Animated conic-gradient ring that transitions smoothly
- Large enough to read from three metres away
- Tone label: "Low", "Elevated", or "High" coordination signal

### Signal Breakdown
- Horizontal bars, one per signal, showing contribution
- Signal keys rendered as human-readable labels (underscores replaced with spaces)
- Explanation string visible inline below each bar
- Dynamic — renders only the signal keys present in the payload

### Agent Table
- Columns: agent ID, last price, PnL, current pair risk, side
- Color-coded risk pills (high / mid / low)
- Positive PnL highlighted in mint green

### Case Panel
- List of cases with status badge and colored status dot
- Truncated transaction hashes
- Group (agent pair) and opened-at-tick metadata
- "Submit Challenge" button for OPEN cases
- Status-specific labels: "Policy review pending", "Policy compliance verified", "Requires escalation review"

### WebSocket Client Hook
- Auto-reconnect with 1.5-second retry interval
- Three visible connection states: Live stream, Reconnecting, Demo stream
- Never shows a white screen — demo mode with seed data when no backend is connected
- Processes tick, risk, and case messages in real time
- Caps tick buffer at 600 points to prevent memory growth

### Scenario Selector
- Dropdown with three scenarios: Competitive, Cartel, Legitimate coordination
- POSTs to `/run/start` when a backend is connected
- No-op in demo mode

### Mock Server (`frontend/mock_server.py`)
- FastAPI server (~30 lines) serving static JSON for every REST route
- WebSocket endpoint replaying a 600-tick fixture at 20 frames per second
- Risk score ramps from 20 to 90 over the replay
- Shock ticks at t=180 and t=360
- Risk payloads sent every 20 ticks with dynamic score and verdict

### Design System
- EB Garamond serif font throughout
- Dark theme with mint green, amber, and red accent colors
- 8px spacing system
- Consistent panel, card, table, and button styles
- Subtle borders, rounded corners, restrained shadows
- Generous whitespace and clear visual hierarchy
- Fully responsive: desktop, laptop, tablet, mobile

### Integration Readiness
- Single env var `VITE_API_URL` switches from demo mode to a real backend
- No mock imports in production components
- No other code changes needed to swap backends
- Frozen interface contract — no renamed keys

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 |
| Language | TypeScript |
| Build tool | Vite |
| Charts | Recharts |
| Icons | Lucide React |
| Styling | Tailwind CSS + custom CSS |
| Mock server | Python / FastAPI |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+ (only for the mock server)

### Install and run (demo mode, no backend needed)

```bash
npm install
npm run dev
```

The dashboard loads with seed data and a visible "Demo stream" connection state.

### Run with the mock server

1. Start the mock server:

```bash
cd frontend
pip install fastapi uvicorn
uvicorn mock_server:app --port 8000
```

2. In a separate terminal, set the API URL and start the dashboard:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

The connection state switches to "Live stream" and data flows over WebSocket.

### Connect to a real backend

Set `VITE_API_URL` to the backend URL. No other code changes are required.

---

## Interface Contract

### REST Routes

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/health` | Service health check |
| GET | `/scenarios` | List available scenarios |
| POST | `/run/start` | Start a simulation run |
| GET | `/run/{id}/status` | Check run status |
| GET | `/risk/latest?run_id=` | Latest risk assessment |
| GET | `/cases` | List all cases |
| POST | `/case/{id}/challenge` | Submit a challenge |
| GET | `/metrics` | System metrics |

### WebSocket

`/ws/live` streams messages of type `tick`, `risk`, or `case`, each with a `payload` object.

---

## Project Structure

```
frontend/
  mock_server.py              FastAPI mock server
  src/
    types.ts                  Shared TypeScript types
    hooks/
      useLiveFeed.ts          WebSocket client hook with auto-reconnect
    components/
      CurrencyAnimation.tsx   3D CSS hero animation
      PriceChart.tsx          Recharts line chart
      RiskGauge.tsx           Animated conic-gradient gauge
      SignalBars.tsx          Horizontal signal contribution bars
      AgentTable.tsx          Agent activity table
      CasePanel.tsx           Case list with status badges
      ScenarioPicker.tsx      Scenario dropdown
    mocks/
      risk.json               Mock risk payload
      cases.json              Mock case records
      scenarios.json          Mock scenario list

src/
  App.tsx                     Main application (pages, layout, routing)
  index.css                   Global styles, design system, animations

demo/
  script.md                   4-minute demo run sheet
  deck/
    slides.md                 8-slide presentation deck
```

---

## Copy Rules

The dashboard uses careful, non-accusatory language throughout:

- The score is labeled "Coordination Risk: 87/100" — never "87% probability of collusion"
- Case statuses use "under review", "cleared", "escalated" — never "guilty"
- Challenge results use "policy compliance verified" — not "innocence proven"

---

## Testing Checklist

- [ ] `npm run dev` works against `mock_server.py` with no backend needed
- [ ] Gauge animates 20 → 60 → 90 with no layout shift
- [ ] Chart handles 600 points without lag
- [ ] Case panel renders all four statuses (OPEN, CHALLENGED, CLEARED, ESCALATED)
- [ ] WebSocket disconnect shows a "reconnecting" state — never a white screen
- [ ] Missing signal keys render gracefully (no empty bars or errors)
- [ ] Readable at 1280x720 from three metres away
- [ ] No console errors
