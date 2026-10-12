import type { AskRequest, AskResponse, SSEEvent, SSEFrame, Source } from "../types";
import { AskHttpError } from "../types";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL || DEFAULT_API_URL;
}

/**
 * Wraps a single TextDecoder instance so a multi-byte UTF-8 character
 * (e.g. an Arabic letter) split across two network chunks is decoded
 * correctly: TextDecoder buffers an incomplete trailing sequence internally
 * and only emits it once the rest arrives, but only if the SAME instance is
 * reused across calls (it must never be re-created per chunk).
 */
export function createSSEDecoder(): { decodeChunk: (chunk: Uint8Array) => string } {
  const decoder = new TextDecoder("utf-8");
  return {
    decodeChunk(chunk: Uint8Array): string {
      return decoder.decode(chunk, { stream: true });
    },
  };
}

/**
 * Pure: given everything decoded so far, pull out every complete frame
 * (terminated by a blank line) and return the still-incomplete tail so the
 * caller can prepend it to the next chunk. Frames can be split at an
 * arbitrary offset by the network, including mid-JSON-object.
 */
export function extractFrames(buffer: string): { frames: SSEFrame[]; remainder: string } {
  const blocks = buffer.split("\n\n");
  // The last element is either "" (buffer ended exactly on a boundary) or an
  // incomplete trailing block to carry forward.
  const remainder = blocks.pop() ?? "";
  const frames: SSEFrame[] = [];
  for (const block of blocks) {
    const frame = parseFrameBlock(block);
    if (frame) frames.push(frame);
  }
  return { frames, remainder };
}

/** Pure: parse one "event: X\ndata: Y" block (no surrounding blank lines) into a frame. */
export function parseFrameBlock(block: string): SSEFrame | null {
  let event = "";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  if (!event || dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

/** Pure, total: never throws. Unknown events or bad JSON become a "parse-error" event. */
export function toSSEEvent(frame: SSEFrame): SSEEvent {
  let parsed: unknown;
  try {
    parsed = JSON.parse(frame.data);
  } catch (err) {
    return {
      type: "parse-error",
      raw: frame,
      message: err instanceof Error ? err.message : "Invalid JSON in SSE frame.",
    };
  }

  switch (frame.event) {
    case "sources":
      return { type: "sources", sources: (parsed as { sources: Source[] }).sources };
    case "token":
      return { type: "token", text: (parsed as { text: string }).text };
    case "done":
      return { type: "done", response: parsed as AskResponse };
    case "error": {
      const data = parsed as { status: number; detail: string };
      return { type: "error", status: data.status, detail: data.detail };
    }
    default:
      return { type: "parse-error", raw: frame, message: `Unknown SSE event "${frame.event}".` };
  }
}

export interface AskStreamHandlers {
  onEvent: (event: SSEEvent) => void;
  signal?: AbortSignal;
}

/**
 * Calls POST /ask/stream and drives the SSE loop. Pre-stream HTTP errors
 * (422/502/503) throw an AskHttpError; once the stream itself starts,
 * every event (including a mid-stream "error" frame) is delivered through
 * onEvent so the caller keeps a single place to react to failures there.
 */
export async function askStream(request: AskRequest, handlers: AskStreamHandlers): Promise<void> {
  const response = await fetch(`${getApiUrl()}/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: handlers.signal,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // Body wasn't JSON; fall back to statusText already assigned above.
    }
    throw new AskHttpError(response.status, detail);
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = createSSEDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decodeChunk(value);
    const { frames, remainder } = extractFrames(buffer);
    buffer = remainder;
    for (const frame of frames) {
      handlers.onEvent(toSSEEvent(frame));
    }
  }
}
