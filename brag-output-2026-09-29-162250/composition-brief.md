# Hyperframes Composition Brief: Guardian Nexus

## Objective
Create a short cinematic launch-style brag video for Guardian Nexus — a real-time voice fraud detection dashboard.

## Output
- Composition directory: `brag-output-2026-09-29-162250/composition/`
- Rendered video: `brag-output-2026-09-29-162250/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `/Users/apple/Documents/GUARDIAN-NEXUS`
- Primary files read: `frontend/app/page.tsx`, `frontend/app/globals.css`, `frontend/components/dashboard/live-sentinel.tsx`, `frontend/components/dashboard/scam-alert-banner.tsx`
- Product name: Guardian Nexus
- Tagline / strongest claim: "Real-time voice fraud detection powered by AssemblyAI"
- Key UI or visual moment to recreate: The 270° LiveSentinel gauge going from Clear to Critical
- Copy that must appear verbatim:
  - "Guardian Nexus"
  - "SCAM ATTEMPT DETECTED"
  - "Real-time voice defense."

## Creative Direction
- Tone preset: cinematic
- Creative direction: dramatic enterprise security reveal — the moment a scam is caught
- Interpretation: Big, confident motion. Dramatic wipes. Dark backgrounds with glowing accents. The pace is deliberate, not rushed. Every reveal lands with weight.
- Angle: Show the product catching a scammer in real-time — the session starts, the transcript flows, the risk spikes, the alert fires.
- Hook: A glowing radar gauge at zero, pulsing in the dark. A cursor clicks "Start Session."
- Outro / punchline: "Guardian Nexus." centered on deep indigo. "Real-time voice defense." below.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign

## Visual Identity
- Background: `#0f172a` (slate-900 for drama) with radial indigo glow
- Text: `#f8fafc` (slate-50 white)
- Accent: `#2563EB` (blue-600 primary), `#E11D48` (rose-600 for critical alert)
- Display font: Inter (800 weight for headlines)
- Body font: Inter (500 weight)
- Strongest visual element: The LiveSentinel 270° gauge with radar sweep and color transitions (emerald → amber → rose)

## Storyboard
Use the storyboard in `brag-output-2026-09-29-162250/brag-plan.md` as the creative contract.

Scene summary:
1. The Hook — 4s — Gauge at zero with radar sweep. Cursor clicks "Start Session."
2. The Analysis — 6s — Transcript feeds in. Waveform bounces. Gauge climbs 0→35→85.
3. The Alert — 5s — ScamAlertBanner slams in with hazard stripes. "SCAM ATTEMPT DETECTED."
4. Outro — 5s — "Guardian Nexus" / "Real-time voice defense." on indigo bg.

## Audio
- Audio role: cinematic support
- Audio arc: Low ambient start → building tension → heavy impact on alert → resolving fade
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: Start at 0s, volume 0.35, fade under during alert scene, fade out in last 2s
- Music cue guidance: detect at composition via hyperframes beats
- Audio-reactive treatment: subtle; use music RMS/bass to make gauge glow and background depth breathe
- Audio-coupled moments:
  - Scene 1 — mouseclick on "Start Session"
  - Scene 2 — soft reveals as transcript appears
  - Scene 3 — heavy bell impact on alert slam
  - Scene 4 — cinematic bell on logo reveal
- SFX selection guidance: cinematic tone — 2-3 big bell impacts. impactBell_heavy for hero and outro. impactSoft_medium for the reveal. mouseclick1 for the button click.
- SFX analysis guidance: see sfx-analysis.md
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume.
- Audio files: copied into `brag-output-2026-09-29-162250/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-cli`. /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer.
- Run `hyperframes check` before render.
