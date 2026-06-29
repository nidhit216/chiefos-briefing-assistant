"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Mode = "work" | "personal";

const STORAGE_KEY = "chiefos_mode";

interface ModeState {
  mode: Mode;
  setMode: (mode: Mode) => void;
}

const ModeContext = createContext<ModeState | null>(null);

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<Mode>("work");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "work" || stored === "personal") {
      setModeState(stored);
    }
  }, []);

  function setMode(next: Mode) {
    setModeState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }

  return (
    <ModeContext.Provider value={{ mode, setMode }}>
      <div data-mode={mode}>{children}</div>
    </ModeContext.Provider>
  );
}

export function useMode() {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error("useMode must be used within ModeProvider");
  return ctx;
}
