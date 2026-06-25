import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-muted mb-3">
          Office of the CEO
        </p>
        <h1 className="font-serif text-5xl text-ink mb-4">ChiefOS</h1>
        <p className="text-xl text-ink-muted mb-2">AI Personal Chief of Staff</p>
        <p className="text-lg text-ink-muted/70 mb-8">
          &ldquo;What should I focus on today?&rdquo;
        </p>
        <Link
          href="/login"
          className="inline-block bg-primary-700 text-white px-8 py-3 rounded-md text-lg font-medium hover:bg-primary-800 transition-colors"
        >
          Get Started
        </Link>
      </div>
    </main>
  );
}
