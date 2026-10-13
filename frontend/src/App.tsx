import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { EmptyState } from "./components/EmptyState";
import { Chat, type TurnViewModel } from "./components/Chat";
import { InputDock } from "./components/InputDock";
import { useAsk, type UseAskResult } from "./hooks/useAsk";
import { useThemeState, ThemeContext } from "./hooks/useTheme";
import { useProvider } from "./hooks/useProvider";
import { LangContext, loadStoredLang, storeLang, t as translate, type UiLang } from "./i18n";

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
  const ask = useAsk();
  const { provider, setProvider } = useProvider();
  const [turns, setTurns] = useState<TurnViewModel[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const idCounter = useRef(0);

  const handleAsk = (question: string) => {
    if (currentId && ask.phase !== "idle") {
      setTurns((prev) => [...prev, snapshotTurn(currentId, ask)]);
    }
    const id = `turn-${idCounter.current++}`;
    setCurrentId(id);
    ask.ask(question, provider);
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
    <div className="relative isolate flex min-h-svh flex-col">
      <div aria-hidden="true" className="page-glow pointer-events-none fixed inset-x-0 top-0 -z-10 h-[420px]" />
      <Header
        onNewConversation={handleNewConversation}
        canStartNew={!isEmpty}
        provider={provider}
        onProviderChange={setProvider}
      />

      {isEmpty ? (
        <EmptyState onPick={handleAsk} />
      ) : (
        <Chat
          turns={allTurns}
          onSwitchToCloud={provider === "ollama" ? () => setProvider("groq") : undefined}
        />
      )}

      <InputDock onSubmit={handleAsk} onStop={ask.stop} isStreaming={ask.phase === "streaming"} provider={provider} />
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
