import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MessageAnswer } from "./MessageAnswer";
import { LangContext, t } from "../i18n";
import type { AskResponse, RefusalReason } from "../types";

afterEach(cleanup);

function makeResponse(provider: string, refusalReason: RefusalReason): AskResponse {
  return {
    question: "q",
    answer: refusalReason ? "Je n'ai pas trouvé la réponse dans les documents disponibles." : "Réponse [1].",
    refused: refusalReason !== null,
    refusal_reason: refusalReason,
    language: "fr",
    best_score: 0.7,
    citations: [],
    sources: [],
    invalid_citations: [],
    provider,
    model: provider === "groq" ? "openai/gpt-oss-120b" : "qwen2.5:7b",
    prompt_tokens: 10,
    completion_tokens: 5,
    timings: { embed_ms: 1, retrieval_ms: 1, generation_ms: 1, total_ms: 3, first_token_ms: null },
  };
}

function renderAnswer(response: AskResponse, onSwitchToCloud = vi.fn<() => void>()) {
  render(
    <LangContext value={{ lang: "en", setLang: () => {}, t: (key, vars) => t(key, "en", vars) }}>
      <MessageAnswer
        turnId="turn-0"
        sources={response.sources}
        streamedText=""
        finalResponse={response}
        isStreaming={false}
        showWarmingUp={false}
        onSwitchToCloud={onSwitchToCloud}
      />
    </LangContext>,
  );
  return onSwitchToCloud;
}

describe("MessageAnswer: switch-to-Cloud hint follows the turn's own provider", () => {
  it("is hidden under a model_declined refusal produced by Groq", () => {
    renderAnswer(makeResponse("groq", "model_declined"));
    expect(screen.getByText("The model could not answer")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Switch to Cloud/ })).toBeNull();
    expect(screen.queryByText("Try again, or switch to the cloud model.")).toBeNull();
  });

  it("is shown under a model_declined refusal produced by Ollama, and switches on click", () => {
    const onSwitch = renderAnswer(makeResponse("ollama", "model_declined"));
    const button = screen.getByRole("button", { name: /Switch to Cloud/ });
    fireEvent.click(button);
    expect(onSwitch).toHaveBeenCalledTimes(1);
  });
});

describe("MessageAnswer: documents' dates", () => {
  it("adds the dates to the verification reminder under a normal answer", () => {
    renderAnswer(makeResponse("ollama", null));
    expect(screen.getByText(/Check the cited source before relying on this answer\./)).toBeTruthy();
    expect(screen.getByText(/The documents date from 2004 \(Labor Code, Arabic\) and 2007/)).toBeTruthy();
  });

  it("mentions the dates on a below_threshold refusal, not on model_declined", () => {
    renderAnswer(makeResponse("ollama", "below_threshold"));
    expect(screen.getByText("No answer found in the documents")).toBeTruthy();
    expect(screen.getByText("The available documents do not seem to cover this question.")).toBeTruthy();
    expect(screen.getByText(/The documents date from 2004/)).toBeTruthy();
    cleanup();

    renderAnswer(makeResponse("ollama", "model_declined"));
    expect(screen.queryByText(/The documents date from 2004/)).toBeNull();
  });
});
