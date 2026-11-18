import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-32 text-center">
      <p className="text-6xl font-black text-gradient">404</p>
      <p className="mt-4 text-subtle">This page fell further than gold in 2013. It hasn&apos;t recovered.</p>
      <Link href="/" className="mt-6 inline-block font-semibold text-brand">← Back home</Link>
    </div>
  );
}
