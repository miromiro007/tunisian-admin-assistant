import { useCallback, useEffect, useRef, useState } from "react";
import { askStream } from "../api/askStream";
import type { AskRequest, AskResponse, Provider, Source } from "../types";
import { AskHttpError } from "../types";

export type AskPhase = "idle" | "streaming" | "done" | "refused" | "error" | "aborted";
export type ErrorKind = "validation" | "rateLimit" | "serviceUnavailable" | "network" | null;

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

/** Maps an HTTP status (pre-stream response or in-stream `error` event) to a user-facing error kind. */
export function errorKindForStatus(status: number): Exclude<ErrorKind, "network" | null> {
  if (status === 422) return "validation";
  if (status === 429) return "rateLimit";
  return "serviceUnavailable";
}

export interface UseAskResult extends UseAskState {
  ask: (question: string, provider?: Provider) => void;
  stop: () => void;
  retry: () => void;
  reset: () => void;
}

export function useAsk(): UseAskResult {
  const [state, setState] = useState<UseAskState>(idleState);
  const controllerRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasReceivedAnyEventRef = useRef(false);
  const lastRequestRef = useRef<AskRequest | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const run = useCallback(
    (request: AskRequest) => {
      controllerRef.current?.abort();
      clearTimer();

      const controller = new AbortController();
      controllerRef.current = controller;
      hasReceivedAnyEventRef.current = false;
      lastRequestRef.current = request;
      // A superseded request (new question, retry, reset) must never write into the current state.
      const isCurrent = () => controllerRef.current === controller;

      setState({ ...idleState, phase: "streaming", question: request.question });

      timerRef.current = setTimeout(() => {
        if (isCurrent() && !hasReceivedAnyEventRef.current) {
          setState((prev) => (prev.phase === "streaming" ? { ...prev, showWarmingUp: true } : prev));
        }
      }, WARMING_UP_DELAY_MS);

      askStream(request, {
        signal: controller.signal,
        onEvent: (event) => {
          if (!isCurrent()) return;
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
              // May arrive with zero preceding tokens (refusals, non-streaming providers like Groq).
              setState((prev) => ({
                ...prev,
                phase: event.response.refused ? "refused" : "done",
                finalResponse: event.response,
                sources: event.response.sources,
                showWarmingUp: false,
              }));
              break;
            case "error":
              setState((prev) => ({ ...prev, phase: "error", errorKind: errorKindForStatus(event.status) }));
              break;
            case "parse-error":
              // Swallow: a malformed frame shouldn't crash the UI. Logged for diagnostics only.
              console.error("Malformed SSE frame", event.raw, event.message);
              break;
          }
        },
      }).catch((err: unknown) => {
        if (!isCurrent()) return;
        clearTimer();
        if (err instanceof DOMException && err.name === "AbortError") {
          setState((prev) => ({ ...prev, phase: "aborted" }));
          return;
        }
        if (err instanceof AskHttpError) {
          setState((prev) => ({ ...prev, phase: "error", errorKind: errorKindForStatus(err.status) }));
          return;
        }
        setState((prev) => ({ ...prev, phase: "error", errorKind: "network" }));
      });
    },
    [clearTimer],
  );

  const ask = useCallback(
    (question: string, provider?: Provider) => {
      const request: AskRequest = { question };
      if (provider) request.provider = provider;
      run(request);
    },
    [run],
  );

  const stop = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const retry = useCallback(() => {
    const last = lastRequestRef.current;
    if (last) run(last);
  }, [run]);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
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
