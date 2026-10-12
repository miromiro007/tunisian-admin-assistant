import { describe, expect, it } from "vitest";
import { createSSEDecoder, extractFrames, toSSEEvent } from "./askStream";
import type { SSEEvent } from "../types";

function sse(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

describe("extractFrames", () => {
  it("parses a single complete frame", () => {
    const { frames, remainder } = extractFrames(sse("token", { text: "hi" }));
    expect(frames).toEqual([{ event: "token", data: '{"text":"hi"}' }]);
    expect(remainder).toBe("");
  });

  it("carries an incomplete trailing frame forward as the remainder", () => {
    const full = sse("token", { text: "hello" });
    const incomplete = full.slice(0, -2); // drop the trailing "\n\n": frame is not yet terminated
    const { frames, remainder } = extractFrames(incomplete);
    expect(frames).toEqual([]);
    expect(remainder).toBe(incomplete);

    // Once the rest arrives, the frame completes.
    const { frames: frames2, remainder: remainder2 } = extractFrames(remainder + "\n\n");
    expect(frames2).toEqual([{ event: "token", data: '{"text":"hello"}' }]);
    expect(remainder2).toBe("");
  });

  it("reassembles a frame split across arbitrary chunk boundaries, including mid-JSON", () => {
    const full = sse("token", { text: "bonjour le monde" });
    // Split well inside the JSON object, at several different offsets.
    for (let cut = 1; cut < full.length - 1; cut += 7) {
      const first = full.slice(0, cut);
      const second = full.slice(cut);
      const step1 = extractFrames(first);
      const step2 = extractFrames(step1.remainder + second);
      const allFrames = [...step1.frames, ...step2.frames];
      expect(allFrames).toEqual([{ event: "token", data: '{"text":"bonjour le monde"}' }]);
    }
  });

  it("extracts multiple frames present in one buffer", () => {
    const buffer = sse("sources", { sources: [] }) + sse("token", { text: "a" });
    const { frames, remainder } = extractFrames(buffer);
    expect(frames).toHaveLength(2);
    expect(frames[0]?.event).toBe("sources");
    expect(frames[1]?.event).toBe("token");
    expect(remainder).toBe("");
  });
});

describe("createSSEDecoder", () => {
  it("decodes a multi-byte Arabic character split across two chunk boundaries", () => {
    const text = "مرحبا بكم"; // Arabic: multi-byte UTF-8 sequences throughout
    const bytes = new TextEncoder().encode(text);
    const decoder = createSSEDecoder();

    // Split at every possible byte offset; some will land mid-character.
    let reassembled = "";
    for (let cut = 1; cut < bytes.length; cut++) {
      const d = createSSEDecoder();
      const part1 = d.decodeChunk(bytes.slice(0, cut));
      const part2 = d.decodeChunk(bytes.slice(cut));
      expect(part1 + part2).toBe(text);
    }

    // Also confirm the single shared-decoder loop pattern used by askStream.
    reassembled += decoder.decodeChunk(bytes.slice(0, 3));
    reassembled += decoder.decodeChunk(bytes.slice(3));
    expect(reassembled).toBe(text);
  });

  it("decodes a full SSE frame containing Arabic text split mid-character", () => {
    const frameText = sse("token", { text: "السلام عليكم" });
    const bytes = new TextEncoder().encode(frameText);
    const decoder = createSSEDecoder();
    const cut = Math.floor(bytes.length / 2) + 1; // arbitrary, likely mid-character
    const decoded = decoder.decodeChunk(bytes.slice(0, cut)) + decoder.decodeChunk(bytes.slice(cut));
    expect(decoded).toBe(frameText);
    const { frames } = extractFrames(decoded);
    expect(JSON.parse(frames[0]!.data)).toEqual({ text: "السلام عليكم" });
  });
});

describe("toSSEEvent", () => {
  it("parses a sources event", () => {
    const event = toSSEEvent({ event: "sources", data: '{"sources":[]}' });
    expect(event).toEqual({ type: "sources", sources: [] });
  });

  it("parses a token event", () => {
    const event = toSSEEvent({ event: "token", data: '{"text":"hi"}' });
    expect(event).toEqual({ type: "token", text: "hi" });
  });

  it("parses an error event", () => {
    const event = toSSEEvent({
      event: "error",
      data: '{"status":503,"detail":"The database is not available."}',
    });
    expect(event).toEqual({ type: "error", status: 503, detail: "The database is not available." });
  });

  it("returns a parse-error for malformed JSON instead of throwing", () => {
    const event = toSSEEvent({ event: "token", data: "{not json" });
    expect(event.type).toBe("parse-error");
  });

  it("returns a parse-error for an unknown event name", () => {
    const event = toSSEEvent({ event: "mystery", data: "{}" });
    expect(event.type).toBe("parse-error");
  });
});

describe("refusal flow", () => {
  it("produces exactly sources then done(refused:true), with zero token events", () => {
    const refusedResponse = {
      question: "q",
      answer: "Not found in the documents.",
      refused: true,
      refusal_reason: "below_threshold",
      language: "fr",
      best_score: 0.1,
      citations: [],
      sources: [],
      invalid_citations: [],
      provider: "ollama",
      model: "qwen2.5:7b",
      prompt_tokens: 0,
      completion_tokens: 0,
      timings: { embed_ms: 1, retrieval_ms: 1, generation_ms: 1, total_ms: 3, first_token_ms: null },
    };
    const buffer = sse("sources", { sources: [] }) + sse("done", refusedResponse);
    const { frames } = extractFrames(buffer);
    const events: SSEEvent[] = frames.map(toSSEEvent);

    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ type: "sources", sources: [] });
    expect(events[1]).toMatchObject({ type: "done", response: { refused: true } });
    expect(events.filter((e) => e.type === "token")).toHaveLength(0);
  });
});
