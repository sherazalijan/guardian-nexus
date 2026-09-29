'use client';

import { create } from 'zustand';
import {
  ConnectionStatus,
  MicStatus,
  TranscriptChunkData,
  RiskResult,
  ProtectionEvent,
  TimelineEvent,
  EvidenceItem,
  Intervention,
  InterventionStatus,
  VoiceSignal,
  VoicePattern,
  InterventionAlertEvent,
  GuardianAlertFrame,
  KnownThreatMatch,
  SessionSummaryData,
  SessionIntelligenceData,
  InterventionHistoryData,
  GatewayErrorData
} from '@/lib/types';

interface GuardianState {
  connectionStatus: ConnectionStatus;
  micStatus: MicStatus;
  sessionId: string | null;
  sessionStartedAt: number | null;
  transcripts: TranscriptChunkData[];
  latestRisk: RiskResult | null;
  riskHistory: RiskResult[];
  protectionEvents: ProtectionEvent[];
  timelineEvents: TimelineEvent[];
  timeline: TimelineEvent[]; // Alias for timelineEvents
  evidenceItems: EvidenceItem[];
  interventions: Intervention[];
  voiceSignals: VoiceSignal[];
  voicePatterns: VoicePattern[];
  interventionAlerts: InterventionAlertEvent[];
  guardianAlerts: GuardianAlertFrame[];
  knownThreatMatches: KnownThreatMatch[];
  sessionSummary: SessionSummaryData | null;
  sessionIntelligence: SessionIntelligenceData | null;
  interventionHistory: InterventionHistoryData | null;
  errors: GatewayErrorData[];

  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  setMicStatus: (status: MicStatus) => void;
  startSession: (sessionId: string) => void;
  pushTranscript: (chunk: TranscriptChunkData) => void;
  pushRisk: (risk: RiskResult) => void;
  pushProtectionEvent: (event: ProtectionEvent) => void;
  pushTimelineEvent: (event: TimelineEvent) => void;
  pushEvidence: (item: EvidenceItem) => void;
  pushIntervention: (intervention: Intervention) => void;
  updateInterventionStatus: (id: string, status: InterventionStatus) => void;
  pushVoiceSignal: (signal: VoiceSignal) => void;
  pushVoicePattern: (pattern: VoicePattern) => void;
  pushInterventionAlert: (event: InterventionAlertEvent) => void;
  pushGuardianAlert: (alert: GuardianAlertFrame) => void;
  pushKnownThreatMatch: (match: KnownThreatMatch) => void;
  setSessionSummary: (summary: SessionSummaryData) => void;
  setSessionIntelligence: (intel: SessionIntelligenceData) => void;
  setInterventionHistory: (history: InterventionHistoryData) => void;
  pushError: (code: string, message: string) => void;
  reset: () => void;
}

const initialState = {
  connectionStatus: 'idle' as ConnectionStatus,
  micStatus: 'inactive' as MicStatus,
  sessionId: null,
  sessionStartedAt: null,
  transcripts: [],
  latestRisk: null,
  riskHistory: [],
  protectionEvents: [],
  timelineEvents: [],
  timeline: [],
  evidenceItems: [],
  interventions: [],
  voiceSignals: [],
  voicePatterns: [],
  interventionAlerts: [],
  guardianAlerts: [],
  knownThreatMatches: [],
  sessionSummary: null,
  sessionIntelligence: null,
  interventionHistory: null,
  errors: [],
};

export const useGuardianStore = create<GuardianState>((set) => ({
  ...initialState,

  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setMicStatus: (status) => set({ micStatus: status }),
  
  startSession: (sessionId) => set({ 
    sessionId, 
    sessionStartedAt: Date.now(), 
    connectionStatus: 'connected' 
  }),

  pushTranscript: (chunk) => set((state) => ({ 
    transcripts: [...state.transcripts, chunk] 
  })),

  pushRisk: (risk) => set((state) => ({ 
    latestRisk: risk, 
    riskHistory: [...state.riskHistory, risk] 
  })),

  pushProtectionEvent: (event) => set((state) => ({ 
    protectionEvents: [...state.protectionEvents, event] 
  })),

  pushTimelineEvent: (event) => set((state) => {
    const newEvents = [...state.timelineEvents, event].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    return { timelineEvents: newEvents, timeline: newEvents };
  }),

  pushEvidence: (item) => set((state) => ({ 
    evidenceItems: [...state.evidenceItems, item] 
  })),

  pushIntervention: (intervention) => set((state) => ({ 
    interventions: [...state.interventions, intervention] 
  })),

  updateInterventionStatus: (id, status) => set((state) => ({
    interventions: state.interventions.map((inv) => 
      inv.intervention_id === id ? { ...inv, status } : inv
    )
  })),

  pushVoiceSignal: (signal) => set((state) => ({ 
    voiceSignals: [...state.voiceSignals, signal] 
  })),

  pushVoicePattern: (pattern) => set((state) => ({ 
    voicePatterns: [...state.voicePatterns, pattern] 
  })),

  pushInterventionAlert: (event) => set((state) => ({ 
    interventionAlerts: [...state.interventionAlerts, event] 
  })),

  pushGuardianAlert: (alert) => set((state) => {
    const existingIndex = state.guardianAlerts.findIndex(a => a.alert_id === alert.alert_id);
    if (existingIndex >= 0) {
      const newAlerts = [...state.guardianAlerts];
      newAlerts[existingIndex] = alert;
      return { guardianAlerts: newAlerts };
    }
    return { guardianAlerts: [...state.guardianAlerts, alert] };
  }),

  pushKnownThreatMatch: (match) => set((state) => ({ 
    knownThreatMatches: [...state.knownThreatMatches, match] 
  })),

  setSessionSummary: (summary) => set({ sessionSummary: summary }),
  
  setSessionIntelligence: (intel) => set({ sessionIntelligence: intel }),
  
  setInterventionHistory: (history) => set({ interventionHistory: history }),

  pushError: (code, message) => set((state) => ({
    errors: [...state.errors, { code, message }]
  })),

  reset: () => set(initialState),
}));
