import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-brain-bg text-white">
      <Link
        href="/ui"
        className="rounded-2xl border border-white/10 px-4 py-2 text-sm bg-white/5 hover:bg-white/10"
      >
        Open BRAiN UI
      </Link>
    </main>
  );
}
