import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { EmptyState } from "./components/EmptyState";
import { Chat, type TurnViewModel } from "./components/Chat";
import { InputDock } from "./components/InputDock";
import { useAsk, type UseAskResult } from "./hooks/useAsk";
import { useThemeState, ThemeContext } from "./hooks/useTheme";
import { LangContext, loadStoredLang, storeLang, t as translate, useLang, type UiLang } from "./i18n";

function snapshotTurn(id: string, ask: UseAskResult): TurnViewModel {
  return {
    id,
    question: ask.question,
    phase: ask.phase,
    sources: ask.sources,
    streamedText: ask.streamedText,
    finalResponse: ask.finalResponse,
    errorKind: ask.errorKind,
    showWarmingUp: ask.showWarmingUp,
  };
}

function AppInner() {
  const { t } = useLang();
  const ask = useAsk();
  const [turns, setTurns] = useState<TurnViewModel[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const idCounter = useRef(0);

  const handleAsk = (question: string) => {
    if (currentId && ask.phase !== "idle") {
      setTurns((prev) => [...prev, snapshotTurn(currentId, ask)]);
    }
    const id = `turn-${idCounter.current++}`;
    setCurrentId(id);
    ask.ask(question);
  };

  const handleNewConversation = () => {
    ask.reset();
    setTurns([]);
    setCurrentId(null);
  };

  const liveTurn: TurnViewModel | null = currentId
    ? {
        id: currentId,
        question: ask.question,
        phase: ask.phase,
        sources: ask.sources,
        streamedText: ask.streamedText,
        finalResponse: ask.finalResponse,
        errorKind: ask.errorKind,
        showWarmingUp: ask.showWarmingUp,
        onRetry: ask.retry,
        onStop: ask.stop,
      }
    : null;

  const allTurns = liveTurn ? [...turns, liveTurn] : turns;
  const isEmpty = allTurns.length === 0;

  return (
    <div className="flex min-h-svh flex-col">
      <Header onNewConversation={handleNewConversation} canStartNew={!isEmpty} />

      {isEmpty ? <EmptyState onPick={handleAsk} /> : <Chat turns={allTurns} />}

      <InputDock onSubmit={handleAsk} onStop={ask.stop} isStreaming={ask.phase === "streaming"} />

      <footer className="border-t border-(--color-border) px-4 py-2 text-center">
        <p className="mx-auto max-w-[760px] text-[0.7rem] text-(--color-text-muted)">
          {t("footer.disclaimer")}
        </p>
      </footer>
    </div>
  );
}

function App() {
  const theme = useThemeState();
  const [lang, setLangState] = useState<UiLang>(() => loadStoredLang());

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = (next: UiLang) => {
    storeLang(next);
    setLangState(next);
  };

  return (
    <ThemeContext value={theme}>
      <LangContext value={{ lang, setLang, t: (key, vars) => translate(key, lang, vars) }}>
        <AppInner />
      </LangContext>
    </ThemeContext>
  );
}

export default App;
