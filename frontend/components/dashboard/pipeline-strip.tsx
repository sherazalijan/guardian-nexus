"use client";

export function PipelineStrip() {
  const steps = [
    ["Microphone", "Browser captures call audio"],
    ["WebSocket", "Audio streams to FastAPI"],
    ["AssemblyAI", "Real-time transcription of every phrase"],
    ["Risk engine", "Scores intent and pressure tactics"],
    ["Live dashboard", "Score, alert and transcript update at once"],
  ];
  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm mt-6">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">How a call becomes a live alert</h2>
      <ol className="flex flex-col gap-2 lg:flex-row lg:items-center">
        {steps.map(([t, d], i) => (
          <li key={t} className="flex flex-1 items-center gap-2">
            <div className={`flex-1 rounded-xl p-3 ${i === 2 ? "bg-gradient-to-br from-indigo-50 to-white ring-2 ring-indigo-500 shadow-[0_8px_24px_-10px_rgb(79_70_229/.45)]" : "bg-slate-50 ring-1 ring-slate-200"}`}>
              <p className={`text-[13px] font-bold ${i === 2 ? "text-indigo-800" : "text-slate-900"}`}>{t}</p>
              <p className={`text-xs ${i === 2 ? "text-indigo-700" : "text-slate-500"}`}>{d}</p>
            </div>
            {i < steps.length - 1 && <span aria-hidden className="hidden text-slate-400 lg:block">→</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
