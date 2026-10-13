import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MessageAnswer } from "./MessageAnswer";
import { ErrorBanner } from "./ErrorBanner";
import { BrandMark } from "./BrandMark";
import type { AskPhase, ErrorKind } from "../hooks/useAsk";
import type { AskResponse, Source } from "../types";

export interface TurnViewModel {
  id: string;
  question: string;
  phase: AskPhase;
  sources: Source[];
  streamedText: string;
  finalResponse: AskResponse | null;
  errorKind: ErrorKind;
  showWarmingUp: boolean;
  onRetry?: () => void;
  onStop?: () => void;
}

interface ChatProps {
  turns: TurnViewModel[];
}

export function Chat({ turns }: ChatProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-1 flex-col gap-8 px-4 pb-8 pt-6 sm:pt-10">
      <AnimatePresence initial={false}>
        {turns.map((turn) => (
          <motion.article
            key={turn.id}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex flex-col gap-4"
          >
            <div className="flex justify-end">
              <p
                className="bidi-plaintext max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-ee-md bg-linear-to-br from-accent-600 to-accent-700 px-4 py-2.5 text-[0.9rem] leading-relaxed text-white shadow-soft"
                dir="auto"
              >
                {turn.question}
              </p>
            </div>

            {turn.phase !== "aborted" && (
              <div className="flex gap-3">
                <div className="pt-0.5">
                  <BrandMark size="sm" />
                </div>
                <div className="min-w-0 flex-1">
                  {turn.phase === "error" ? (
                    <ErrorBanner kind={turn.errorKind} onRetry={() => turn.onRetry?.()} />
                  ) : (
                    <MessageAnswer
                      turnId={turn.id}
                      sources={turn.sources}
                      streamedText={turn.streamedText}
                      finalResponse={turn.finalResponse}
                      isStreaming={turn.phase === "streaming"}
                      showWarmingUp={turn.showWarmingUp}
                    />
                  )}
                </div>
              </div>
            )}
          </motion.article>
        ))}
      </AnimatePresence>
    </div>
  );
}
