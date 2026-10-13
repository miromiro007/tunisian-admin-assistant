import { useState } from "react";
import type { Provider } from "../types";

const STORAGE_KEY = "provider";
const DEFAULT_PROVIDER: Provider = "ollama";

function loadStoredProvider(): Provider {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "ollama" || stored === "groq") return stored;
  } catch {
    // localStorage unavailable (private mode, etc.) - fall back to default.
  }
  return DEFAULT_PROVIDER;
}

export function useProvider(): { provider: Provider; setProvider: (provider: Provider) => void } {
  const [provider, setProviderState] = useState<Provider>(loadStoredProvider);

  const setProvider = (next: Provider) => {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore - per-viewer convenience only.
    }
    setProviderState(next);
  };

  return { provider, setProvider };
}
