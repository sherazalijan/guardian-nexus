# Guardian Nexus — Dashboard

Next.js 15 / TypeScript / Tailwind / shadcn-style dashboard for the
Guardian Nexus `/ws/audio` gateway: live transcript, risk alerts, and a
threat timeline, with an offline **Demo Mode** that needs no backend.

## Run

```bash
npm install
cp .env.local.example .env.local   # optional — defaults already match the backend
npm run dev
```

Open http://localhost:3000.

- **Live mode** (default): connects to `ws://localhost:8000/ws/audio`
  (override with `NEXT_PUBLIC_GUARDIAN_WS_URL`), requests microphone
  access on "Start session", and streams PCM16/16kHz audio to the
  backend.
- **Demo mode**: toggle "Demo" before starting a session. Plays back a
  scripted call (`lib/mock-data.ts`) — partial and final transcripts,
  escalating risk assessments, and a sample `error` frame — on the same
  message shapes and timing a real session uses. No mic, no backend.

## Testing without a backend

1. `npm run dev`, open the dashboard.
2. Leave the toggle on **Demo** and click **Start session**.
3. Confirm: connection status goes idle → connecting → connected;
   transcript lines appear in the Live Audio panel; the Risk Alert panel
   updates through low → medium → high severity; the Threat Timeline logs
   every transcript, risk event, and the sample error; **End session**
   returns everything to idle.

## Testing against the real backend

1. In `GUARDIAN-NEXUS/backend`: `uvicorn app.main:app --reload` (see the
   backend README for env setup; `ASSEMBLYAI_PROVIDER=mock` needs no API
   key and will echo one fixed transcript per connection).
2. Here: toggle **Live**, click **Start session**, allow microphone
   access.
3. Confirm the connection badge reaches "Connected", transcripts stream
   in, and a `risk` frame follows each final transcript. Stop the
   backend mid-session to see "Reconnecting…" (only if the backend's
   `ASSEMBLYAI_MAX_RECONNECTS` reconnect wrapper is enabled — otherwise
   the socket closes and the dashboard reports a connection error, which
   is also worth confirming).

## Architecture

```
app/
  layout.tsx            wraps the app in GuardianSessionProvider
  page.tsx               the dashboard screen
providers/
  guardian-session-provider.tsx   picks live vs. demo gateway, owns mic capture
hooks/
  use-websocket-gateway.ts  real /ws/audio client (connect/reconnect/disconnect)
  use-mock-gateway.ts       same interface, scripted playback, no network
  use-audio-capture.ts      mic -> PCM16 chunks
store/
  guardian-store.ts       Zustand: connection/mic status, timeline, latest risk
components/dashboard/    panels (live audio, risk alert, threat timeline, ...)
components/ui/           shadcn-style primitives (button, card, badge, ...)
lib/
  types.ts                wire types, mirrors the backend's /ws/audio frames
  mock-data.ts             Demo Mode's scripted call
```

State management is Zustand (`store/guardian-store.ts`); the only
Context is `GuardianSessionProvider`, which exists purely to give the
dashboard one `startSession()` / `stopSession()` pair without prop-drilling
a socket and a `MediaStream` through the tree.
