import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { askStream, type AskStreamHandlers } from "../api/askStream";
import { AskHttpError, type AskRequest, type AskResponse, type SSEEvent } from "../types";
import { errorKindForStatus, useAsk } from "./useAsk";

vi.mock("../api/askStream", () => ({ askStream: vi.fn<typeof askStream>() }));
const mockedAskStream = vi.mocked(askStream);

function makeResponse(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    question: "q",
    answer: "Réponse complète [1].",
    refused: false,
    refusal_reason: null,
    language: "fr",
    best_score: 0.8,
    citations: [],
    sources: [],
    invalid_citations: [],
    provider: "groq",
    model: "llama-3.3-70b-versatile",
    prompt_tokens: 10,
    completion_tokens: 5,
    timings: { embed_ms: 1, retrieval_ms: 1, generation_ms: 1, total_ms: 3, first_token_ms: null },
    ...overrides,
  };
}

/** Makes the mocked askStream emit the given events, then resolve. */
function emitting(events: SSEEvent[]) {
  return async (_request: AskRequest, handlers: AskStreamHandlers) => {
    for (const event of events) handlers.onEvent(event);
  };
}

afterEach(() => {
  cleanup();
  mockedAskStream.mockReset();
});

describe("useAsk", () => {
  it("handles sources then done with no token event (non-streaming provider like Groq)", async () => {
    const response = makeResponse();
    mockedAskStream.mockImplementation(emitting([{ type: "sources", sources: [] }, { type: "done", response }]));

    const { result } = renderHook(() => useAsk());
    act(() => result.current.ask("Quelle est la durée ?", "groq"));

    await waitFor(() => expect(result.current.phase).toBe("done"));
    expect(result.current.streamedText).toBe("");
    expect(result.current.finalResponse?.answer).toBe("Réponse complète [1].");
  });

  it("handles the Groq path: sources, then the whole answer as ONE token, then done", async () => {
    const bigAnswer = `${"Selon l'article 5, l'employeur verse les cotisations avant le 15 du mois suivant [1]. ".repeat(40)}`;
    const response = makeResponse({ answer: bigAnswer });
    let releaseDone!: () => void;
    const doneGate = new Promise<void>((resolve) => {
      releaseDone = resolve;
    });

    mockedAskStream.mockImplementation(async (_request, handlers) => {
      handlers.onEvent({ type: "sources", sources: [] });
      handlers.onEvent({ type: "token", text: bigAnswer });
      await doneGate;
      handlers.onEvent({ type: "done", response });
    });

    const { result } = renderHook(() => useAsk());
    act(() => result.current.ask("Délai de versement ?", "groq"));

    // Between the single token and `done`: the full text is already visible, still streaming.
    await waitFor(() => expect(result.current.streamedText).toBe(bigAnswer));
    expect(result.current.phase).toBe("streaming");
    expect(result.current.finalResponse).toBeNull();

    await act(async () => releaseDone());
    await waitFor(() => expect(result.current.phase).toBe("done"));
    expect(result.current.finalResponse?.answer).toBe(bigAnswer);
    expect(result.current.errorKind).toBeNull();
  });

  it("sends the selected provider in the request body and reuses it on retry", async () => {
    mockedAskStream.mockImplementation(emitting([{ type: "error", status: 503, detail: "down" }]));

    const { result } = renderHook(() => useAsk());
    act(() => result.current.ask("Question test", "groq"));
    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(mockedAskStream.mock.calls[0]?.[0]).toEqual({ question: "Question test", provider: "groq" });

    act(() => result.current.retry());
    await waitFor(() => expect(mockedAskStream).toHaveBeenCalledTimes(2));
    expect(mockedAskStream.mock.calls[1]?.[0]).toEqual({ question: "Question test", provider: "groq" });
  });

  it("maps a pre-stream HTTP 429 to the rateLimit error kind", async () => {
    mockedAskStream.mockRejectedValue(new AskHttpError(429, "Too Many Requests"));

    const { result } = renderHook(() => useAsk());
    act(() => result.current.ask("Question test", "groq"));

    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.errorKind).toBe("rateLimit");
  });

  it("maps an in-stream error event with status 429 to the rateLimit error kind", async () => {
    mockedAskStream.mockImplementation(
      emitting([
        { type: "sources", sources: [] },
        { type: "error", status: 429, detail: "rate limited" },
      ]),
    );

    const { result } = renderHook(() => useAsk());
    act(() => result.current.ask("Question test", "groq"));

    await waitFor(() => expect(result.current.phase).toBe("error"));
    expect(result.current.errorKind).toBe("rateLimit");
  });
});

describe("errorKindForStatus", () => {
  it("maps statuses to user-facing error kinds", () => {
    expect(errorKindForStatus(422)).toBe("validation");
    expect(errorKindForStatus(429)).toBe("rateLimit");
    expect(errorKindForStatus(502)).toBe("serviceUnavailable");
    expect(errorKindForStatus(503)).toBe("serviceUnavailable");
  });
});
