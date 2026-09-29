# Guardian Nexus 🛡️

**Built for the AssemblyAI Hackathon**

Guardian Nexus is a high-performance, enterprise-grade real-time voice fraud defense platform. It actively monitors live audio streams, detects intent, and automatically initiates system lockdowns before scammers can compromise user data.

## 🚀 Powered by AssemblyAI

At the core of Guardian Nexus is **AssemblyAI's Real-time Streaming API**. By tapping into live audio feeds, Guardian Nexus instantly transcribes caller audio with ultra-low latency. We then pass these transcripts through our proprietary threat vector detection algorithms to gauge risk levels dynamically. 

When AssemblyAI detects key social engineering phrases (e.g., "I need your card number to verify your identity"), Guardian Nexus spikes the threat gauge, triggers a visual scam alert banner, and initiates an immediate system lockdown.

### Key Features
- **Real-Time Voice Defense**: Leverages AssemblyAI for instant audio-to-text processing.
- **Dynamic Threat Scoring**: Gauges confidence and identifies threat vectors on the fly.
- **Immediate Lockdown**: Visual alerts and instant intervention protocols when critical thresholds are breached.
- **Enterprise Dashboard**: A modern, intensive cyber-security themed UI (vibrant colors, glassmorphism, dynamic animations).

## 🛠 Tech Stack
- **AI/Audio**: AssemblyAI Real-time API
- **Frontend**: React (Vite), Zustand, Tailwind CSS / Vanilla CSS, Recharts
- **Backend**: FastAPI, WebSockets, SQLAlchemy (Async), PostgreSQL
- **Video Composition**: Hyperframes & GSAP

## 📦 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- An AssemblyAI API Key

### Backend Setup
1. Navigate to the `backend/` directory.
2. Create a `.env` file and add your `ASSEMBLYAI_API_KEY`.
3. Install dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```
4. Run the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```

## 🎥 Demo Video
Check out our launch video generated entirely using Hyperframes and GSAP in the `brag-output-*` folder! It showcases the exact moment AssemblyAI intercepts a threat and the system goes into lockdown.
