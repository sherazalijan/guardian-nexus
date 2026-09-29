"use client";

import { useCallback, useRef } from "react";
import { useGuardianStore } from "@/store/guardian-store";

export interface UseAudioCaptureOptions {
  onAudioChunk: (chunk: ArrayBuffer) => void;
}

export interface UseAudioCaptureResult {
  start: () => Promise<void>;
  stop: () => void;
}

export function useAudioCapture({
  onAudioChunk,
}: UseAudioCaptureOptions): UseAudioCaptureResult {
  const contextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  const setMicStatus = useGuardianStore((s) => s.setMicStatus);

  const start = useCallback(async () => {
    setMicStatus("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const context = new AudioContext({ sampleRate: 16000 });
      contextRef.current = context;

      const source = context.createMediaStreamSource(stream);
      sourceRef.current = source;

      // ScriptProcessorNode is deprecated but has widest browser support
      // for real-time PCM extraction without an AudioWorklet
      const processor = context.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e: AudioProcessingEvent) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        onAudioChunk(pcm16.buffer);
      };

      source.connect(processor);
      processor.connect(context.destination);

      setMicStatus("active");
    } catch (err: unknown) {
      const isDenied =
        err instanceof DOMException &&
        (err.name === "NotAllowedError" ||
          err.name === "PermissionDeniedError");
      setMicStatus(isDenied ? "denied" : "error");
      throw err;
    }
  }, [onAudioChunk, setMicStatus]);

  const stop = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (contextRef.current && contextRef.current.state !== "closed") {
      contextRef.current.close();
      contextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setMicStatus("inactive");
  }, [setMicStatus]);

  return { start, stop };
}
