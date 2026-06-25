"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import Toast from "@/app/components/Toast";

interface BriefGenerationState {
  generating: boolean;
  generationVersion: number;
  generate: () => void;
  cancel: () => void;
}

const BriefGenerationContext = createContext<BriefGenerationState | null>(null);

export function BriefGenerationProvider({ children }: { children: React.ReactNode }) {
  const [generating, setGenerating] = useState(false);
  const [generationVersion, setGenerationVersion] = useState(0);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const generate = useCallback(() => {
    if (abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setGenerating(true);

    (async () => {
      try {
        const res = await apiFetch("/briefs/generate", {
          method: "POST",
          signal: controller.signal,
        });
        if (res.ok) {
          setToast({ message: "Brief generated successfully", type: "success" });
        } else {
          const err = await res.json().catch(() => null);
          setToast({
            message: err?.detail || `Could not generate brief (${res.status}).`,
            type: "error",
          });
        }
      } catch (err) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          setToast({ message: "Could not reach the server to generate brief.", type: "error" });
        }
      } finally {
        setGenerating(false);
        abortRef.current = null;
        setGenerationVersion((v) => v + 1);
      }
    })();
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
    <BriefGenerationContext.Provider value={{ generating, generationVersion, generate, cancel }}>
      {children}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </BriefGenerationContext.Provider>
  );
}

export function useBriefGeneration() {
  const ctx = useContext(BriefGenerationContext);
  if (!ctx) throw new Error("useBriefGeneration must be used within BriefGenerationProvider");
  return ctx;
}
