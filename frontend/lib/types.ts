/**
 * Guardian Nexus — Frontend type definitions.
 *
 * Mirrors every backend Pydantic model and enum that appears on the
 * `/ws/audio` WebSocket wire protocol.  Keep these in sync with
 * `backend/app/models/` — the backend is the source of truth.
 */

// ─── Enums ──────────────────────────────────────────────────────────

export type ThreatSeverity = "low" | "medium" | "high" | "critical";

export type ThreatCategory =
  | "scam"
  | "phishing"
  | "impersonation"
  | "malware"
  | "fraud"
  | "suspicious_call"
  | "malicious_link"
  | "unknown";

export type RecommendedAction =
  | "ignore"
  | "monitor"
  | "warn"
  | "block"
  | "escalate";

export type EvidenceState = "insufficient" | "partial" | "sufficient";

export type ProtectionEventType =
  | "threat_detected"
  | "risk_escalated"
  | "warning"
  | "critical_alert"
  | "sensitive_information_detected"
  | "recommended_action"
  | "session_summary";

export type ProtectionState =
  | "monitoring"
  | "suspicious"
  | "high_risk"
  | "critical";

export type SecurityCategory =
  | "otp_theft"
  | "bank_impersonation"
  | "account_compromise"
  | "urgent_payment"
  | "gift_card_scam"
  | "cryptocurrency_scam"
  | "remote_access_scam"
  | "phishing"
  | "credential_theft"
  | "social_engineering"
  | "unknown";

export type InterventionPriority = "none" | "medium" | "high" | "critical";

export type InterventionStatus =
  | "active"
  | "acknowledged"
  | "escalated"
  | "resolved"
  | "expired";

export type AlertLevel = "info" | "warning" | "high_risk" | "critical";

export type AlertStatus = "active" | "acknowledged" | "dismissed" | "expired";

export type VoiceSignalType =
  | "authority_impersonation"
  | "technical_support_impersonation"
  | "account_compromise_claim"
  | "urgency_pressure"
  | "threat_intimidation"
  | "sensitive_information_request"
  | "payment_request"
  | "gift_card_request"
  | "crypto_request"
  | "remote_access_request"
  | "secrecy_isolation"
  | "verification_bypass"
  | "emotional_manipulation";

export type InterventionLevel = "info" | "warning" | "high_risk" | "critical";

export type IncidentEventType =
  | "session_started"
  | "evidence_detected"
  | "threat_detected"
  | "risk_escalated"
  | "risk_decreased"
  | "warning"
  | "critical_alert"
  | "recommended_action"
  | "state_changed";

export type RiskHistoryTrigger =
  | "initial"
  | "risk_increase"
  | "risk_decrease"
  | "severity_change"
  | "critical_escalation";

export type EvidenceSource = "transcript";

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

export type MicStatus = "inactive" | "requesting" | "active" | "denied" | "error";

// ─── Data models ────────────────────────────────────────────────────

export interface TranscriptChunkData {
  text: string;
  is_final: boolean;
  confidence: number;
}

export interface RiskFactor {
  name: string;
  description: string;
  contribution: number;
}

export interface RiskResult {
  score: number;
  severity: ThreatSeverity;
  confidence: number;
  evidence_state: EvidenceState;
  risk_factors: RiskFactor[];
  explanation: string;
  recommended_action: RecommendedAction;
}

export interface ProtectionEvent {
  event_id: string;
  session_id: string;
  timestamp: string;
  event_type: ProtectionEventType;
  severity: ThreatSeverity;
  risk_score: number;
  title: string;
  message: string;
  category: SecurityCategory;
  evidence: string[];
  recommended_action: string;
  confidence: number;
}

export interface TimelineEvent {
  event_id: string;
  session_id: string;
  timestamp: string;
  label: string;
  category: SecurityCategory | null;
  severity: ThreatSeverity | null;
  detail: string | null;
  metadata: Record<string, unknown>;
}

export interface EvidenceItem {
  evidence_id: string;
  session_id: string;
  timestamp: string;
  source: EvidenceSource;
  text: string;
  signal: string;
  category: SecurityCategory;
  severity: ThreatSeverity;
  risk_score: number;
  confidence: number;
}

export interface Intervention {
  intervention_id: string;
  session_id: string;
  timestamp: string;
  priority: InterventionPriority;
  risk_score: number;
  title: string;
  message: string;
  category: SecurityCategory;
  recommended_action: string;
  requires_acknowledgement: boolean;
  status: InterventionStatus;
  source_event_id: string | null;
  evidence: string[];
  escalated_from: string | null;
}

export interface InterventionAckResult {
  success: boolean;
  reason: string;
  intervention_id: string | null;
  status: InterventionStatus | null;
}

export interface VoiceSignal {
  signal_id: string;
  session_id: string;
  signal_type: VoiceSignalType;
  category: ThreatCategory;
  confidence: number;
  severity: ThreatSeverity;
  evidence_text: string;
  timestamp: string;
  source: string;
  metadata: Record<string, unknown>;
}

export interface VoicePattern {
  pattern_id: string;
  session_id: string;
  pattern_type: string;
  signals: VoiceSignalType[];
  confidence: number;
  evidence: string[];
  timestamp: string;
}

export interface VoiceIntelligenceData {
  signals: VoiceSignal[];
  patterns: VoicePattern[];
}

export interface InterventionAlertEvent {
  id: string;
  timestamp: string;
  level: InterventionLevel;
  title: string;
  message: string;
  confidence: number;
  source: string;
  risk_score: number;
  category: ThreatCategory | null;
}

export interface GuardianAlertFrame {
  alert_id: string;
  level: AlertLevel;
  status: AlertStatus;
  title: string;
  message: string;
  risk_score: number;
  confidence: number;
  timestamp: string;
}

export interface KnownThreatMatch {
  threat_id: string;
  match_score: number;
  category: string;
  matched_indicators: string[];
  occurrence_count: number;
}

export interface RiskHistoryEntry {
  timestamp: string;
  previous_score: number;
  new_score: number;
  severity: ThreatSeverity;
  state: ProtectionState;
  trigger: RiskHistoryTrigger;
}

export interface IncidentTimelineEvent {
  timeline_event_id: string;
  session_id: string;
  timestamp: string;
  event_type: IncidentEventType;
  title: string;
  description: string;
  severity: ThreatSeverity | null;
  risk_score: number | null;
  category: SecurityCategory | null;
  evidence_ids: string[];
}

export interface SessionSummaryData {
  session_id: string;
  session_started_at: string | null;
  session_ended_at: string | null;
  duration_seconds: number | null;
  highest_risk_score: number;
  final_risk_score: number;
  highest_severity: ThreatSeverity;
  detected_categories: SecurityCategory[];
  detected_signals: string[];
  warning_count: number;
  critical_alert_count: number;
  recommended_final_action: string;
  /* Phase 2 additive keys */
  evidence_count?: number;
  primary_category?: SecurityCategory;
  risk_escalation_count?: number;
  final_state?: ProtectionState;
  /* Phase 3 additive keys */
  intervention_count?: number;
  critical_intervention_occurred?: boolean;
}

export interface SessionIntelligenceData {
  session_id: string;
  started_at: string;
  updated_at: string;
  current_state: ProtectionState;
  current_risk_score: number;
  highest_risk_score: number;
  highest_severity: ThreatSeverity;
  primary_category: SecurityCategory;
  categories: SecurityCategory[];
  signals: string[];
  evidence: EvidenceItem[];
  timeline: IncidentTimelineEvent[];
  warnings: number;
  critical_alerts: number;
  recommended_actions: string[];
  risk_history: RiskHistoryEntry[];
}

export interface InterventionHistoryData {
  session_id: string;
  interventions: Intervention[];
}

// ─── Legacy mock compatibility ──────────────────────────────────────

/** Shape used by the existing mock-data script. */
export interface RiskAnalysisData {
  transcript: string;
  scam_score: number;
  category: string;
  explanation: string;
  risk_level: string;
  risk_result: RiskResult;
}

export interface GatewayErrorData {
  code: string;
  message: string;
}

// ─── WebSocket frame envelope ───────────────────────────────────────

export type WSFrameType =
  | "connected"
  | "transcript"
  | "risk"
  | "protection"
  | "timeline"
  | "evidence"
  | "intervention"
  | "intervention_ack_result"
  | "voice_intelligence"
  | "intervention_alert"
  | "guardian_alert"
  | "known_threat_match"
  | "session_summary"
  | "session_intelligence"
  | "intervention_history"
  | "error";

export interface WSFrame {
  type: WSFrameType;
  data?: unknown;
  error?: GatewayErrorData;
  /* guardian_alert has flat top-level fields */
  alert_id?: string;
  level?: string;
  status?: string;
  title?: string;
  message?: string;
  risk_score?: number;
  confidence?: number;
  timestamp?: string;
}

// ─── Helpers ────────────────────────────────────────────────────────

export const SEVERITY_ORDER: Record<ThreatSeverity, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

export const PROTECTION_STATE_ORDER: Record<ProtectionState, number> = {
  monitoring: 0,
  suspicious: 1,
  high_risk: 2,
  critical: 3,
};

export function severityLabel(s: ThreatSeverity): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatSignalType(t: VoiceSignalType): string {
  return t
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatCategory(c: SecurityCategory | string): string {
  return c
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatProtectionState(s: ProtectionState): string {
  return s
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function riskStateFromScore(score: number): ProtectionState {
  if (score >= 78) return "critical";
  if (score >= 52) return "high_risk";
  if (score >= 25) return "suspicious";
  return "monitoring";
}
