"use client";

import { useCallback, useEffect, useRef } from "react";
import { useGuardianStore } from "@/store/guardian-store";
import type { RiskResult, VoiceSignal, VoicePattern } from "@/lib/types";

export interface UseWebSocketGatewayOptions {
  onClose?: () => void;
}

export interface UseWebSocketGatewayResult {
  connect: () => void;
  disconnect: () => void;
  sendAudio: (chunk: ArrayBuffer) => void;
  acknowledgeIntervention: (interventionId: string) => void;
}

const MAX_RECONNECT_ATTEMPTS = 3;

export function useWebSocketGateway(
  options: UseWebSocketGatewayOptions = {}
): UseWebSocketGatewayResult {
  const { onClose } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);

  const setConnectionStatus = useGuardianStore((s) => s.setConnectionStatus);
  const startSession = useGuardianStore((s) => s.startSession);
  const pushTranscript = useGuardianStore((s) => s.pushTranscript);
  const pushRisk = useGuardianStore((s) => s.pushRisk);
  const pushProtectionEvent = useGuardianStore((s) => s.pushProtectionEvent);
  const pushTimelineEvent = useGuardianStore((s) => s.pushTimelineEvent);
  const pushEvidence = useGuardianStore((s) => s.pushEvidence);
  const pushIntervention = useGuardianStore((s) => s.pushIntervention);
  const updateInterventionStatus = useGuardianStore((s) => s.updateInterventionStatus);
  const pushVoiceSignal = useGuardianStore((s) => s.pushVoiceSignal);
  const pushVoicePattern = useGuardianStore((s) => s.pushVoicePattern);
  const pushInterventionAlert = useGuardianStore((s) => s.pushInterventionAlert);
  const pushGuardianAlert = useGuardianStore((s) => s.pushGuardianAlert);
  const pushKnownThreatMatch = useGuardianStore((s) => s.pushKnownThreatMatch);
  const setSessionSummary = useGuardianStore((s) => s.setSessionSummary);
  const setSessionIntelligence = useGuardianStore((s) => s.setSessionIntelligence);
  const setInterventionHistory = useGuardianStore((s) => s.setInterventionHistory);
  const pushError = useGuardianStore((s) => s.pushError);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      if (typeof event.data !== "string") return;

      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      const type = payload.type as string;

      switch (type) {
        case "connected":
          startSession(`session-${Date.now()}`);
          break;
        case "transcript":
          pushTranscript(payload.data as { text: string; is_final: boolean; confidence: number });
          break;
        case "risk":
          pushRisk(payload.data as RiskResult);
          break;
        case "protection":
          pushProtectionEvent(payload.data as Parameters<typeof pushProtectionEvent>[0]);
          break;
        case "timeline":
          pushTimelineEvent(payload.data as Parameters<typeof pushTimelineEvent>[0]);
          break;
        case "evidence":
          pushEvidence(payload.data as Parameters<typeof pushEvidence>[0]);
          break;
        case "intervention":
          pushIntervention(payload.data as Parameters<typeof pushIntervention>[0]);
          break;
        case "intervention_ack_result": {
          const ackData = payload.data as { intervention_id?: string; status?: string };
          if (ackData?.intervention_id && ackData?.status) {
            updateInterventionStatus(
              ackData.intervention_id,
              ackData.status as Parameters<typeof updateInterventionStatus>[1]
            );
          }
          break;
        }
        case "voice_intelligence": {
          const viData = payload.data as { signals?: VoiceSignal[]; patterns?: VoicePattern[] };
          if (viData?.signals) {
            for (const s of viData.signals) pushVoiceSignal(s);
          }
          if (viData?.patterns) {
            for (const p of viData.patterns) pushVoicePattern(p);
          }
          break;
        }
        case "intervention_alert":
          pushInterventionAlert(payload.data as Parameters<typeof pushInterventionAlert>[0]);
          break;
        case "guardian_alert":
          // Flat structure — fields are top-level, not nested in data
          pushGuardianAlert({
            alert_id: payload.alert_id as string,
            level: payload.level as string,
            status: payload.status as string,
            title: payload.title as string,
            message: payload.message as string,
            risk_score: payload.risk_score as number,
            confidence: payload.confidence as number,
            timestamp: payload.timestamp as string,
          } as Parameters<typeof pushGuardianAlert>[0]);
          break;
        case "known_threat_match":
          pushKnownThreatMatch(payload.data as Parameters<typeof pushKnownThreatMatch>[0]);
          break;
        case "session_summary":
          setSessionSummary(payload.data as Parameters<typeof setSessionSummary>[0]);
          break;
        case "session_intelligence":
          setSessionIntelligence(payload.data as Parameters<typeof setSessionIntelligence>[0]);
          break;
        case "intervention_history":
          setInterventionHistory(payload.data as Parameters<typeof setInterventionHistory>[0]);
          break;
        case "error": {
          const err = payload.error as { code?: string; message?: string } | undefined;
          pushError(err?.code ?? "unknown", err?.message ?? "An unknown error occurred.");
          break;
        }
        default:
          break;
      }
    },
    [
      startSession, pushTranscript, pushRisk, pushProtectionEvent,
      pushTimelineEvent, pushEvidence, pushIntervention, updateInterventionStatus,
      pushVoiceSignal, pushVoicePattern, pushInterventionAlert, pushGuardianAlert,
      pushKnownThreatMatch, setSessionSummary, setSessionIntelligence,
      setInterventionHistory, pushError,
    ]
  );

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    intentionalCloseRef.current = false;
    const isReconnect = reconnectAttemptsRef.current > 0;
    setConnectionStatus(isReconnect ? "reconnecting" : "connecting");

    const wsUrl =
      process.env.NEXT_PUBLIC_GUARDIAN_WS_URL || "ws://localhost:8000/ws/audio";

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        // connectionStatus will be set to 'connected' by the 'connected' frame handler
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        wsRef.current = null;

        if (intentionalCloseRef.current) {
          setConnectionStatus("disconnected");
          onClose?.();
          return;
        }

        if (
          !event.wasClean &&
          reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
        ) {
          const backoff = Math.pow(2, reconnectAttemptsRef.current) * 1000;
          reconnectAttemptsRef.current += 1;
          setConnectionStatus("reconnecting");
          reconnectTimerRef.current = setTimeout(connect, backoff);
        } else {
          setConnectionStatus("disconnected");
          onClose?.();
        }
      };

      ws.onerror = () => {
        // onclose will fire after this with wasClean=false
      };
    } catch {
      setConnectionStatus("error");
    }
  }, [setConnectionStatus, handleMessage, onClose]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    clearReconnectTimer();
    reconnectAttemptsRef.current = 0;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionStatus("disconnected");
    onClose?.();
  }, [setConnectionStatus, clearReconnectTimer, onClose]);

  const sendAudio = useCallback((chunk: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk);
    }
  }, []);

  const acknowledgeIntervention = useCallback((interventionId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "acknowledge_intervention",
          intervention_id: interventionId,
        })
      );
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [clearReconnectTimer]);

  return { connect, disconnect, sendAudio, acknowledgeIntervention };
}
