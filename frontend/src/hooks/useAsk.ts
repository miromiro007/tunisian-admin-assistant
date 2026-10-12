import { useCallback, useEffect, useRef, useState } from "react";
import { askStream } from "../api/askStream";
import type { AskRequest, AskResponse, Language, Source } from "../types";
import { AskHttpError } from "../types";

export type AskPhase = "idle" | "streaming" | "done" | "refused" | "error" | "aborted";
export type ErrorKind = "validation" | "serviceUnavailable" | "network" | null;

export interface UseAskState {
  phase: AskPhase;
  question: string;
  sources: Source[];
  streamedText: string;
  finalResponse: AskResponse | null;
  errorKind: ErrorKind;
  showWarmingUp: boolean;
}

const WARMING_UP_DELAY_MS = 4000;

const idleState: UseAskState = {
  phase: "idle",
  question: "",
  sources: [],
  streamedText: "",
  finalResponse: null,
  errorKind: null,
  showWarmingUp: false,
};

export interface UseAskResult extends UseAskState {
  ask: (question: string, language?: Language) => void;
  stop: () => void;
  retry: () => void;
  reset: () => void;
}

export function useAsk(): UseAskResult {
  const [state, setState] = useState<UseAskState>(idleState);
  const controllerRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasReceivedAnyEventRef = useRef(false);
  const lastRequestRef = useRef<{ question: string; language?: Language } | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const run = useCallback(
    (question: string, language?: Language) => {
      controllerRef.current?.abort();
      clearTimer();

      const controller = new AbortController();
      controllerRef.current = controller;
      hasReceivedAnyEventRef.current = false;
      lastRequestRef.current = { question, language };

      setState({ ...idleState, phase: "streaming", question });

      timerRef.current = setTimeout(() => {
        if (!hasReceivedAnyEventRef.current) {
          setState((prev) => (prev.phase === "streaming" ? { ...prev, showWarmingUp: true } : prev));
        }
      }, WARMING_UP_DELAY_MS);

      const request: AskRequest = { question };
      if (language) request.language = language;

      askStream(request, {
        signal: controller.signal,
        onEvent: (event) => {
          hasReceivedAnyEventRef.current = true;
          clearTimer();

          switch (event.type) {
            case "sources":
              setState((prev) => ({ ...prev, sources: event.sources, showWarmingUp: false }));
              break;
            case "token":
              setState((prev) => ({ ...prev, streamedText: prev.streamedText + event.text }));
              break;
            case "done":
              setState((prev) => ({
                ...prev,
                phase: event.response.refused ? "refused" : "done",
                finalResponse: event.response,
                sources: event.response.sources,
              }));
              break;
            case "error":
              setState((prev) => ({ ...prev, phase: "error", errorKind: "serviceUnavailable" }));
              break;
            case "parse-error":
              // Swallow: a malformed frame shouldn't crash the UI. Logged for diagnostics only.
              console.error("Malformed SSE frame", event.raw, event.message);
              break;
          }
        },
      }).catch((err: unknown) => {
        clearTimer();
        if (err instanceof DOMException && err.name === "AbortError") {
          setState((prev) => ({ ...prev, phase: "aborted" }));
          return;
        }
        if (err instanceof AskHttpError) {
          const kind: ErrorKind = err.status === 422 ? "validation" : "serviceUnavailable";
          setState((prev) => ({ ...prev, phase: "error", errorKind: kind }));
          return;
        }
        setState((prev) => ({ ...prev, phase: "error", errorKind: "network" }));
      });
    },
    [clearTimer],
  );

  const ask = useCallback(
    (question: string, language?: Language) => {
      run(question, language);
    },
    [run],
  );

  const stop = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const retry = useCallback(() => {
    const last = lastRequestRef.current;
    if (last) run(last.question, last.language);
  }, [run]);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    clearTimer();
    setState(idleState);
  }, [clearTimer]);

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
      clearTimer();
    };
  }, [clearTimer]);

  return { ...state, ask, stop, retry, reset };
}
