# Guardian Nexus — Frontend Architecture Contract

This document outlines the architecture, data flow, and backend integration requirements for the Guardian Nexus React/Next.js frontend.

## 1. System Architecture

The frontend is a strictly **reactive UI layer**. It does not perform local risk calculation, signal detection, or threat memory lookups. It relies entirely on the streaming intelligence provided by the backend via the `/ws/audio` WebSocket gateway.

### Core Stack
- **Framework**: Next.js 15 (App Router)
- **State Management**: Zustand
- **Styling**: Tailwind CSS v4 + Shadcn UI components
- **Audio Capture**: Browser `MediaRecorder` API (`audio/webm`)

## 2. State Management (Zustand)

The central source of truth for the frontend is `useGuardianStore` (located in `frontend/store/guardian-store.ts`).

- As the WebSocket connection receives JSON payloads, a centralized dispatcher (`useGuardianSession`) parses the `type` field and delegates the payload to the corresponding Zustand `pushX` action.
- React components subscribe to specific slices of this store (e.g., `useGuardianStore(s => s.latestRisk)`) to ensure hyper-efficient re-renders only when their specific data updates.
- **Strict Typing**: The store is strictly typed against the interfaces defined in `frontend/lib/types.ts`. These interfaces must exactly mirror the backend Pydantic models.

## 3. Component Hierarchy & Responsibilities

The primary view is assembled in `app/page.tsx` as a real-time dashboard:

- **`LiveTranscript`**: Displays the streaming conversation. Re-renders frequently as interim chunks arrive.
- **`RiskDisplay`**: Renders a visual SVG gauge representing the `latestRisk.score`. Colors shift from Emerald (Safe) to Destructive Red (Critical).
- **`VoiceIntelligence`**: Visualizes behavioral signals (`voice_signal` and `voice_pattern`) with percentage-based progress bars to explain *why* the AI is suspicious.
- **`InterventionCenter`**: Displays actionable interventions. If an intervention is interactive, it dispatches an `acknowledge_intervention` payload back through the WebSocket.
- **`GuardianAlertBanner`**: A fixed or floating banner for `CRITICAL` or `HIGH_RISK` Guardian Alerts. Must be immediately visible to the user.
- **`ThreatMemory`**: Conditionally renders when a `known_threat_match` event arrives, cross-referencing current indicators with historical attacks.

## 4. WebSocket Lifecycle

1. **Initialization**: When the user clicks "Start Session", the `useAudioCapture` hook requests microphone permissions and begins recording.
2. **Connection**: The `useWebSocketGateway` hook establishes the wss connection to the backend.
3. **Streaming**: As chunks of audio (`audio/webm`) become available from the `MediaRecorder`, they are sent as binary frames over the WebSocket.
4. **Receiving**: Text/JSON frames received from the server are parsed and pushed into the Zustand store.
5. **Termination**: When the session ends, the microphone stream is closed, and the backend broadcasts a `session_summary` before closing the socket.

## 5. Development Mode (Mock Gateway)

For demonstrations and UI development, the frontend includes a **Demo Mode** (`useMockGateway`). 
- This bypasses the actual WebSocket and microphone.
- It replays a hardcoded array of deterministic JSON payloads over 45 seconds to simulate a high-risk OTP theft scenario.
- Component code remains agnostic; it merely consumes the Zustand store regardless of whether the live gateway or mock gateway populated it.
