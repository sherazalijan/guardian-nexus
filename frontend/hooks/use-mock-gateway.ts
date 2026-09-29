"use client";

/**
 * Drop-in stand-in for `useWebSocketGateway` that needs no backend.
 *
 * Same `connect` / `disconnect` / `sendAudio` / `acknowledgeIntervention`
 * shape, so `GuardianSessionProvider` can swap between the real gateway and
 * this one purely based on which "mode" is selected.
 *
 * Plays back a scripted bank-impersonation scam call that exercises every
 * panel: transcript, risk, protection, evidence, voice intelligence,
 * intervention, guardian alert, and threat memory.
 */

import { useCallback, useRef } from "react";
import { useGuardianStore } from "@/store/guardian-store";
import { MOCK_SCRIPT, type MockStep } from "@/lib/mock-data";
import type {
  UseWebSocketGatewayOptions,
  UseWebSocketGatewayResult,
} from "@/hooks/use-websocket-gateway";

const CONNECT_DELAY_MS = 400;

export function useMockGateway(
  options: UseWebSocketGatewayOptions = {}
): UseWebSocketGatewayResult {
  const { onClose } = options;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stoppedRef = useRef(true);

  const setConnectionStatus = useGuardianStore((s) => s.setConnectionStatus);
  const startSession = useGuardianStore((s) => s.startSession);
  const pushTranscript = useGuardianStore((s) => s.pushTranscript);
  const pushRisk = useGuardianStore((s) => s.pushRisk);
  const pushProtectionEvent = useGuardianStore((s) => s.pushProtectionEvent);
  const pushTimelineEvent = useGuardianStore((s) => s.pushTimelineEvent);
  const pushEvidence = useGuardianStore((s) => s.pushEvidence);
  const pushIntervention = useGuardianStore((s) => s.pushIntervention);
  const pushVoiceSignal = useGuardianStore((s) => s.pushVoiceSignal);
  const pushVoicePattern = useGuardianStore((s) => s.pushVoicePattern);
  const pushInterventionAlert = useGuardianStore((s) => s.pushInterventionAlert);
  const pushGuardianAlert = useGuardianStore((s) => s.pushGuardianAlert);
  const pushKnownThreatMatch = useGuardianStore((s) => s.pushKnownThreatMatch);
  const setSessionSummary = useGuardianStore((s) => s.setSessionSummary);
  const pushError = useGuardianStore((s) => s.pushError);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const playFrom = useCallback(
    (index: number) => {
      if (stoppedRef.current || index >= MOCK_SCRIPT.length) return;

      const step: MockStep = MOCK_SCRIPT[index];
      timerRef.current = setTimeout(() => {
        if (stoppedRef.current) return;

        switch (step.type) {
          case "transcript":
            pushTranscript(step.data);
            break;
          case "risk":
            pushRisk(step.data.risk_result);
            break;
          case "protection":
            pushProtectionEvent(step.data);
            break;
          case "timeline":
            pushTimelineEvent(step.data);
            break;
          case "evidence":
            pushEvidence(step.data);
            break;
          case "intervention":
            pushIntervention(step.data);
            break;
          case "voice_signal":
            pushVoiceSignal(step.data);
            break;
          case "voice_pattern":
            pushVoicePattern(step.data);
            break;
          case "intervention_alert":
            pushInterventionAlert(step.data);
            break;
          case "guardian_alert":
            pushGuardianAlert(step.data);
            break;
          case "known_threat_match":
            pushKnownThreatMatch(step.data);
            break;
          case "session_summary":
            setSessionSummary(step.data);
            break;
          case "error":
            pushError(step.data.code, step.data.message);
            break;
        }

        playFrom(index + 1);
      }, step.delayMs);
    },
    [
      pushTranscript, pushRisk, pushProtectionEvent, pushTimelineEvent,
      pushEvidence, pushIntervention, pushVoiceSignal, pushVoicePattern,
      pushInterventionAlert, pushGuardianAlert, pushKnownThreatMatch,
      setSessionSummary, pushError,
    ]
  );

  const connect = useCallback(() => {
    stoppedRef.current = false;
    setConnectionStatus("connecting");

    timerRef.current = setTimeout(() => {
      if (stoppedRef.current) return;
      setConnectionStatus("connected");
      startSession("demo-session");
      playFrom(0);
    }, CONNECT_DELAY_MS);
  }, [playFrom, setConnectionStatus, startSession]);

  const disconnect = useCallback(() => {
    stoppedRef.current = true;
    clearTimer();
    setConnectionStatus("disconnected");
    onClose?.();
  }, [clearTimer, setConnectionStatus, onClose]);

  const sendAudio = useCallback((_chunk: ArrayBuffer) => {
    // No real transport in Demo Mode
  }, []);

  const acknowledgeIntervention = useCallback((_interventionId: string) => {
    // No-op in demo mode
  }, []);

  return { connect, disconnect, sendAudio, acknowledgeIntervention };
}
