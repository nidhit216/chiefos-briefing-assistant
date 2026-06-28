"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import PageShell from "@/app/components/PageShell";
import Toast from "@/app/components/Toast";

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-ink/10 rounded-md bg-cream-50 p-5">
      <h2 className="font-serif text-lg text-ink mb-1">{title}</h2>
      {description && <p className="text-sm text-ink-muted mb-4">{description}</p>}
      <div className="divide-y divide-ink/10">{children}</div>
    </section>
  );
}

function SettingRow({
  label,
  description,
  action,
}: {
  label: string;
  description: string;
  action: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">{label}</p>
        <p className="text-sm text-ink-muted mt-0.5">{description}</p>
      </div>
      <div className="flex-shrink-0">{action}</div>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const [embedding, setEmbedding] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("chiefos_token");
    if (!token) router.push("/login");
  }, [router]);

  const embedData = async () => {
    setEmbedding(true);
    try {
      const res = await apiFetch("/search/embed", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setToast({ message: data.message, type: "success" });
      } else {
        const err = await res.json().catch(() => null);
        setToast({ message: err?.detail || "Embedding failed", type: "error" });
      }
    } catch (_) {
      setToast({ message: "Could not reach server", type: "error" });
    } finally {
      setEmbedding(false);
    }
  };

  return (
    <PageShell maxWidth="max-w-2xl">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      <div className="mb-8">
        <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-1">ChiefOS</p>
        <h1 className="font-serif text-3xl text-ink">Settings</h1>
      </div>

      <div className="space-y-6">
        <SettingsSection
          title="Data & Sync"
          description="Manage how ChiefOS indexes your emails, notes, and calendar for search and Ask."
        >
          <SettingRow
            label="Re-embed all data"
            description="Rebuilds the search index from scratch. Use this after a bulk import, or if Ask and Search results look stale."
            action={
              <button
                onClick={embedData}
                disabled={embedding}
                className="text-sm bg-primary-100 text-primary-800 px-3 py-1.5 rounded-md hover:bg-primary-200 disabled:opacity-50 transition-colors whitespace-nowrap"
              >
                {embedding ? "Embedding..." : "Re-embed all data"}
              </button>
            }
          />
        </SettingsSection>
      </div>
    </PageShell>
  );
}
