import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MessageAnswer } from "./MessageAnswer";
import { ErrorBanner } from "./ErrorBanner";
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
    <div className="mx-auto flex w-full max-w-[760px] flex-1 flex-col gap-6 px-4 py-6">
      <AnimatePresence initial={false}>
        {turns.map((turn) => (
          <motion.div
            key={turn.id}
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="flex flex-col gap-3"
          >
            <div className="flex justify-end">
              <p
                className="bidi-plaintext max-w-[85%] rounded-2xl bg-accent-500 px-4 py-2.5 text-sm text-white"
                dir="auto"
              >
                {turn.question}
              </p>
            </div>

            <div className="flex justify-start">
              <div className="w-full max-w-[85%]">
                {turn.phase === "error" ? (
                  <ErrorBanner kind={turn.errorKind} onRetry={() => turn.onRetry?.()} />
                ) : turn.phase === "aborted" ? null : (
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
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
