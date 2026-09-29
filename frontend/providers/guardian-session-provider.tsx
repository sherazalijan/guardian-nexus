"use client";

/**
 * Owns one Guardian Nexus session end-to-end: picks the WebSocket gateway
 * (real backend vs. offline Demo Mode), owns the microphone capture hook,
 * and wires them together, so dashboard components only call
 * `useGuardianSession()` for session control and read live data from
 * `useGuardianStore`.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { useGuardianStore } from "@/store/guardian-store";
import { useWebSocketGateway } from "@/hooks/use-websocket-gateway";
import { useMockGateway } from "@/hooks/use-mock-gateway";
import { useAudioCapture } from "@/hooks/use-audio-capture";
import type { UseWebSocketGatewayResult } from "@/hooks/use-websocket-gateway";

export type SessionMode = "live" | "demo";

interface GuardianSessionContextValue {
  mode: SessionMode;
  setMode: (mode: SessionMode) => void;
  isBusy: boolean;
  startSession: () => void;
  stopSession: () => void;
  acknowledgeIntervention: (interventionId: string) => void;
}

const GuardianSessionContext =
  createContext<GuardianSessionContextValue | null>(null);

function defaultMode(): SessionMode {
  return process.env.NEXT_PUBLIC_GUARDIAN_MOCK === "1" ? "demo" : "live";
}

export function GuardianSessionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mode, setModeState] = useState<SessionMode>(defaultMode);
  const [isBusy, setIsBusy] = useState(false);

  const reset = useGuardianStore((s) => s.reset);

  const audioCaptureRef = useRef<{ stop: () => void } | null>(null);

  const wsGateway = useWebSocketGateway({
    onClose: () => audioCaptureRef.current?.stop(),
  });
  const mockGateway = useMockGateway({
    onClose: () => audioCaptureRef.current?.stop(),
  });

  const activeGatewayRef = useRef<UseWebSocketGatewayResult>(wsGateway);

  const audioCapture = useAudioCapture({
    onAudioChunk: (chunk) => activeGatewayRef.current.sendAudio(chunk),
  });
  audioCaptureRef.current = audioCapture;

  const setMode = useCallback((next: SessionMode) => {
    setModeState(next);
  }, []);

  const startSession = useCallback(() => {
    setIsBusy(true);
    reset();

    const gateway = mode === "demo" ? mockGateway : wsGateway;
    activeGatewayRef.current = gateway;
    gateway.connect();

    if (mode === "live") {
      audioCapture
        .start()
        .catch(() => {
          // Mic errors surface through micStatus in the store
        })
        .finally(() => setIsBusy(false));
    } else {
      setIsBusy(false);
    }
  }, [mode, mockGateway, wsGateway, audioCapture, reset]);

  const stopSession = useCallback(() => {
    audioCapture.stop();
    activeGatewayRef.current.disconnect();
  }, [audioCapture]);

  const acknowledgeIntervention = useCallback(
    (interventionId: string) => {
      activeGatewayRef.current.acknowledgeIntervention(interventionId);
    },
    []
  );

  const value = useMemo<GuardianSessionContextValue>(
    () => ({
      mode,
      setMode,
      isBusy,
      startSession,
      stopSession,
      acknowledgeIntervention,
    }),
    [mode, setMode, isBusy, startSession, stopSession, acknowledgeIntervention]
  );

  return (
    <GuardianSessionContext.Provider value={value}>
      {children}
    </GuardianSessionContext.Provider>
  );
}

export function useGuardianSession(): GuardianSessionContextValue {
  const ctx = useContext(GuardianSessionContext);
  if (!ctx) {
    throw new Error(
      "useGuardianSession must be used within a GuardianSessionProvider"
    );
  }
  return ctx;
}
