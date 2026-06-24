import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">ChiefOS</h1>
        <p className="text-xl text-gray-600 mb-2">AI Personal Chief of Staff</p>
        <p className="text-lg text-gray-500 mb-8">
          &ldquo;What should I focus on today?&rdquo;
        </p>
        <Link
          href="/login"
          className="inline-block bg-primary-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-primary-700 transition-colors"
        >
          Get Started
        </Link>
      </div>
    </main>
  );
}
