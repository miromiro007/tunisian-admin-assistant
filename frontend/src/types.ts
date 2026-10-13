export type Language = "fr" | "ar";

export type RefusalReason =
  | "no_sources"
  | "below_threshold"
  | "model_declined"
  | "empty_answer"
  | null;

export type Provider = "ollama" | "groq";

export interface AskRequest {
  question: string;
  top_k?: number;
  language?: Language;
  provider?: Provider;
}

export interface Source {
  number: number;
  chunk_id: number | null;
  document: string;
  law_title: string | null;
  article: string | null;
  page: number | null;
  language: string;
  score: number;
  excerpt: string;
  cited: boolean;
}

export interface Timings {
  embed_ms: number;
  retrieval_ms: number;
  generation_ms: number;
  total_ms: number;
  first_token_ms: number | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  refused: boolean;
  refusal_reason: RefusalReason;
  language: Language;
  best_score: number | null;
  citations: Source[];
  sources: Source[];
  invalid_citations: number[];
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  timings: Timings;
}

/** One raw "event: X\ndata: Y\n\n" frame, before its data is JSON-parsed. */
export interface SSEFrame {
  event: string;
  data: string;
}

/** Typed, parsed SSE events as emitted by POST /ask/stream. */
export type SSEEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "done"; response: AskResponse }
  | { type: "error"; status: number; detail: string }
  | { type: "parse-error"; raw: SSEFrame; message: string };

/** A pre-stream HTTP error (422 / 502 / 503), thrown before any SSE frame arrives. */
export class AskHttpError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "AskHttpError";
    this.status = status;
    this.detail = detail;
  }
}
