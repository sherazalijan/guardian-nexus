/**
 * Scripted playback for Demo Mode (`useMockGateway`).
 *
 * A scripted bank-impersonation → OTP-theft scam call that exercises
 * every frontend panel: transcript, risk, protection, evidence, voice
 * intelligence, intervention, guardian alert, and threat memory.
 *
 * Each step's `data` shape matches the exact backend WebSocket payloads.
 */

import type {
  TranscriptChunkData,
  RiskResult,
  ProtectionEvent,
  TimelineEvent,
  EvidenceItem,
  Intervention,
  VoiceSignal,
  VoicePattern,
  InterventionAlertEvent,
  GuardianAlertFrame,
  KnownThreatMatch,
  SessionSummaryData,
  GatewayErrorData,
  RiskAnalysisData,
} from "@/lib/types";

export type MockStep =
  | { type: "transcript"; delayMs: number; data: TranscriptChunkData }
  | { type: "risk"; delayMs: number; data: RiskAnalysisData }
  | { type: "protection"; delayMs: number; data: ProtectionEvent }
  | { type: "timeline"; delayMs: number; data: TimelineEvent }
  | { type: "evidence"; delayMs: number; data: EvidenceItem }
  | { type: "intervention"; delayMs: number; data: Intervention }
  | { type: "voice_signal"; delayMs: number; data: VoiceSignal }
  | { type: "voice_pattern"; delayMs: number; data: VoicePattern }
  | { type: "intervention_alert"; delayMs: number; data: InterventionAlertEvent }
  | { type: "guardian_alert"; delayMs: number; data: GuardianAlertFrame }
  | { type: "known_threat_match"; delayMs: number; data: KnownThreatMatch }
  | { type: "session_summary"; delayMs: number; data: SessionSummaryData }
  | { type: "error"; delayMs: number; data: GatewayErrorData };

const now = () => new Date().toISOString();
let eventSeq = 0;
const eid = () => `demo-evt-${++eventSeq}`;

function benignRisk(transcript: string): RiskAnalysisData {
  return {
    transcript,
    scam_score: 0,
    category: "unknown",
    explanation: "No scam indicators detected.",
    risk_level: "low",
    risk_result: {
      score: 0,
      severity: "low",
      confidence: 0,
      evidence_state: "insufficient",
      risk_factors: [],
      explanation: "Insufficient threat evidence for a reliable assessment.",
      recommended_action: "monitor",
    },
  };
}

export const MOCK_SCRIPT: MockStep[] = [
  // ── Phase 1: Benign opener ───────────────────────────────────────
  {
    type: "timeline",
    delayMs: 100,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      label: "Session started",
      category: null,
      severity: null,
      detail: "Guardian monitoring initiated",
      metadata: {},
    },
  },
  {
    type: "transcript",
    delayMs: 500,
    data: { text: "Hi, is this—", is_final: false, confidence: 0.4 },
  },
  {
    type: "transcript",
    delayMs: 700,
    data: {
      text: "Hi, is this the card holder for the account ending 4471?",
      is_final: true,
      confidence: 0.93,
    },
  },
  {
    type: "risk",
    delayMs: 200,
    data: benignRisk(
      "Hi, is this the card holder for the account ending 4471?"
    ),
  },

  // ── Phase 2: Bank impersonation ─────────────────────────────────
  {
    type: "transcript",
    delayMs: 1400,
    data: {
      text: "This is your bank's fraud department calling about suspicious activity on your account.",
      is_final: true,
      confidence: 0.95,
    },
  },
  {
    type: "risk",
    delayMs: 200,
    data: {
      transcript:
        "This is your bank's fraud department calling about suspicious activity on your account.",
      scam_score: 25,
      category: "impersonation",
      explanation:
        'Detected bank impersonation — calling from "fraud department".',
      risk_level: "medium",
      risk_result: {
        score: 42,
        severity: "medium",
        confidence: 0.75,
        evidence_state: "partial",
        risk_factors: [
          {
            name: "bank_impersonation",
            description:
              'Caller claims to be from bank fraud department (matched: "fraud department")',
            contribution: 0.75,
          },
        ],
        explanation: "Partial threat evidence supports a preliminary assessment.",
        recommended_action: "warn",
      },
    },
  },
  {
    type: "voice_signal",
    delayMs: 100,
    data: {
      signal_id: eid(),
      session_id: "demo-session",
      signal_type: "authority_impersonation",
      category: "impersonation",
      confidence: 0.82,
      severity: "medium",
      evidence_text:
        "Caller identifies as bank fraud department, claiming institutional authority",
      timestamp: now(),
      source: "voice-intelligence-agent",
      metadata: {},
    },
  },
  {
    type: "protection",
    delayMs: 100,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      event_type: "threat_detected",
      severity: "medium",
      risk_score: 42,
      title: "Bank Impersonation Detected",
      message:
        "The caller is claiming to represent your bank's fraud department. Legitimate banks rarely make unsolicited calls requesting account verification.",
      category: "bank_impersonation",
      evidence: [
        'Used phrase "fraud department"',
        "Claims institutional authority",
      ],
      recommended_action:
        "Do not share any account details. Hang up and call your bank directly using the number on your card.",
      confidence: 0.75,
    },
  },
  {
    type: "evidence",
    delayMs: 100,
    data: {
      evidence_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      source: "transcript",
      text: 'Caller claims to be from "bank fraud department" with authority to discuss account activity',
      signal: "bank_impersonation",
      category: "bank_impersonation",
      severity: "medium",
      risk_score: 42,
      confidence: 0.75,
    },
  },
  {
    type: "timeline",
    delayMs: 50,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      label: "Threat detected: Bank Impersonation",
      category: "bank_impersonation",
      severity: "medium",
      detail: "Caller claims bank authority — medium confidence",
      metadata: {},
    },
  },

  // ── Phase 3: Urgency escalation ─────────────────────────────────
  {
    type: "transcript",
    delayMs: 1800,
    data: {
      text: "We've detected unauthorized transactions and need to verify your identity immediately to prevent further losses.",
      is_final: true,
      confidence: 0.94,
    },
  },
  {
    type: "voice_signal",
    delayMs: 100,
    data: {
      signal_id: eid(),
      session_id: "demo-session",
      signal_type: "urgency_pressure",
      category: "scam",
      confidence: 0.78,
      severity: "high",
      evidence_text:
        "Creating false urgency by claiming unauthorized transactions require immediate action",
      timestamp: now(),
      source: "voice-intelligence-agent",
      metadata: {},
    },
  },
  {
    type: "voice_signal",
    delayMs: 50,
    data: {
      signal_id: eid(),
      session_id: "demo-session",
      signal_type: "account_compromise_claim",
      category: "fraud",
      confidence: 0.85,
      severity: "high",
      evidence_text:
        "Claiming the account has been compromised with unauthorized transactions",
      timestamp: now(),
      source: "voice-intelligence-agent",
      metadata: {},
    },
  },
  {
    type: "risk",
    delayMs: 200,
    data: {
      transcript:
        "We've detected unauthorized transactions and need to verify your identity immediately to prevent further losses.",
      scam_score: 58,
      category: "fraud",
      explanation:
        "Multiple scam signals: bank impersonation + urgency pressure + account compromise claim.",
      risk_level: "high",
      risk_result: {
        score: 65,
        severity: "high",
        confidence: 0.82,
        evidence_state: "partial",
        risk_factors: [
          {
            name: "bank_impersonation",
            description: "Claims bank authority",
            contribution: 0.75,
          },
          {
            name: "urgency_pressure",
            description: "Creates false urgency around unauthorized transactions",
            contribution: 0.78,
          },
          {
            name: "account_compromise_claim",
            description: "Claims account is compromised",
            contribution: 0.85,
          },
        ],
        explanation: "Multiple threat indicators support elevated risk assessment.",
        recommended_action: "warn",
      },
    },
  },
  {
    type: "protection",
    delayMs: 100,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      event_type: "risk_escalated",
      severity: "high",
      risk_score: 65,
      title: "Risk Level Elevated",
      message:
        "Multiple scam indicators detected. Caller combines bank impersonation with urgency pressure and account compromise claims.",
      category: "account_compromise",
      evidence: [
        "Bank impersonation detected",
        "False urgency created",
        "Account compromise claims",
      ],
      recommended_action:
        "Exercise extreme caution. Do not share personal information. Consider ending the call.",
      confidence: 0.82,
    },
  },
  {
    type: "timeline",
    delayMs: 50,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      label: "Risk escalated to HIGH",
      category: "account_compromise",
      severity: "high",
      detail: "Multiple scam indicators detected",
      metadata: {},
    },
  },

  // Brief error to test error handling
  {
    type: "error",
    delayMs: 800,
    data: {
      code: "provider_warning",
      message: "Brief audio jitter detected; continuing session.",
    },
  },

  // ── Phase 4: OTP theft attempt (CRITICAL) ───────────────────────
  {
    type: "transcript",
    delayMs: 1400,
    data: {
      text: "We need to verify your identity by reading me the OTP that was just sent to your phone.",
      is_final: true,
      confidence: 0.96,
    },
  },
  {
    type: "voice_signal",
    delayMs: 100,
    data: {
      signal_id: eid(),
      session_id: "demo-session",
      signal_type: "sensitive_information_request",
      category: "phishing",
      confidence: 0.92,
      severity: "critical",
      evidence_text:
        "Requesting OTP / verification code — a one-time password should never be shared with callers",
      timestamp: now(),
      source: "voice-intelligence-agent",
      metadata: {},
    },
  },
  {
    type: "voice_pattern",
    delayMs: 50,
    data: {
      pattern_id: eid(),
      session_id: "demo-session",
      pattern_type: "BANK_OTP_THEFT",
      signals: [
        "authority_impersonation",
        "urgency_pressure",
        "sensitive_information_request",
      ],
      confidence: 0.91,
      evidence: [
        "Bank authority claim + urgency + OTP request = classic OTP theft pattern",
      ],
      timestamp: now(),
    },
  },
  {
    type: "risk",
    delayMs: 200,
    data: {
      transcript:
        "We need to verify your identity by reading me the OTP that was just sent to your phone.",
      scam_score: 88,
      category: "phishing",
      explanation:
        "Critical: OTP theft attempt combined with bank impersonation and urgency pressure.",
      risk_level: "critical",
      risk_result: {
        score: 88,
        severity: "critical",
        confidence: 0.91,
        evidence_state: "sufficient",
        risk_factors: [
          {
            name: "otp_request",
            description:
              'Requested one-time password / verification code (matched: "OTP")',
            contribution: 0.92,
          },
          {
            name: "bank_impersonation",
            description: "Claims bank authority",
            contribution: 0.75,
          },
          {
            name: "urgency_pressure",
            description: "Creates false urgency",
            contribution: 0.78,
          },
        ],
        explanation:
          "Sufficient threat evidence supports the risk assessment. This is a confirmed scam pattern.",
        recommended_action: "escalate",
      },
    },
  },
  {
    type: "protection",
    delayMs: 100,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      event_type: "critical_alert",
      severity: "critical",
      risk_score: 88,
      title: "CRITICAL: OTP Theft Attempt",
      message:
        "The caller is requesting your one-time password. This is a confirmed scam technique. Banks NEVER ask for OTPs over the phone.",
      category: "otp_theft",
      evidence: [
        "Requested OTP/verification code",
        "Combined with bank impersonation",
        "False urgency created",
        "Account compromise claims used as pretext",
      ],
      recommended_action:
        "HANG UP IMMEDIATELY. Do not share your OTP. Call your bank directly.",
      confidence: 0.91,
    },
  },
  {
    type: "evidence",
    delayMs: 50,
    data: {
      evidence_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      source: "transcript",
      text: "Caller directly requested the OTP verification code sent to phone",
      signal: "otp_request",
      category: "otp_theft",
      severity: "critical",
      risk_score: 88,
      confidence: 0.92,
    },
  },
  {
    type: "intervention",
    delayMs: 100,
    data: {
      intervention_id: "int_demo_001",
      session_id: "demo-session",
      timestamp: now(),
      priority: "critical",
      risk_score: 88,
      title: "Immediate Action Required",
      message:
        "A confirmed OTP theft scam has been detected. End this call immediately.",
      category: "otp_theft",
      recommended_action:
        "Hang up immediately. Do not share any codes or passwords. Contact your bank using the number on your card.",
      requires_acknowledgement: true,
      status: "active",
      source_event_id: null,
      evidence: [
        "OTP request detected",
        "Bank impersonation confirmed",
        "Urgency pressure applied",
      ],
      escalated_from: null,
    },
  },
  {
    type: "intervention_alert",
    delayMs: 100,
    data: {
      id: eid(),
      timestamp: now(),
      level: "critical",
      title: "CRITICAL INTERVENTION",
      message:
        "OTP theft scam confirmed. Caller is attempting to steal your verification code.",
      confidence: 0.91,
      source: "intervention-engine",
      risk_score: 88,
      category: "phishing",
    },
  },
  {
    type: "guardian_alert",
    delayMs: 200,
    data: {
      alert_id: "ga-demo-001",
      level: "critical",
      status: "active",
      title: "🛡️ Guardian Alert: Scam Detected",
      message:
        "This call is a confirmed OTP theft scam. The caller is impersonating your bank and attempting to steal your verification code. HANG UP NOW.",
      risk_score: 88,
      confidence: 0.91,
      timestamp: now(),
    },
  },
  {
    type: "timeline",
    delayMs: 50,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      label: "CRITICAL ALERT: OTP Theft Attempt",
      category: "otp_theft",
      severity: "critical",
      detail: "Guardian alert triggered — immediate action recommended",
      metadata: {},
    },
  },
  {
    type: "known_threat_match",
    delayMs: 500,
    data: {
      threat_id: "threat-bank-otp-2024",
      match_score: 0.87,
      category: "otp_theft",
      matched_indicators: [
        "authority_impersonation",
        "urgency_pressure",
        "sensitive_information_request",
        "account_compromise_claim",
      ],
      occurrence_count: 7,
    },
  },
  {
    type: "timeline",
    delayMs: 50,
    data: {
      event_id: eid(),
      session_id: "demo-session",
      timestamp: now(),
      label: "Known threat matched",
      category: "otp_theft",
      severity: "critical",
      detail: "Matches previously seen OTP theft pattern (7 prior occurrences)",
      metadata: {},
    },
  },

  // ── Phase 5: Session summary ────────────────────────────────────
  {
    type: "session_summary",
    delayMs: 2000,
    data: {
      session_id: "demo-session",
      session_started_at: new Date(Date.now() - 45000).toISOString(),
      session_ended_at: now(),
      duration_seconds: 45,
      highest_risk_score: 88,
      final_risk_score: 88,
      highest_severity: "critical",
      detected_categories: [
        "bank_impersonation",
        "otp_theft",
        "account_compromise",
      ],
      detected_signals: [
        "bank_impersonation",
        "urgency_pressure",
        "otp_request",
        "account_compromise_claim",
      ],
      warning_count: 2,
      critical_alert_count: 1,
      recommended_final_action:
        "This was a confirmed scam call. Contact your bank immediately using the number on your card to report this incident.",
      evidence_count: 2,
      primary_category: "otp_theft",
      risk_escalation_count: 3,
      final_state: "critical",
      intervention_count: 1,
      critical_intervention_occurred: true,
    },
  },
];
