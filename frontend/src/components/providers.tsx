"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { API_URL, api, type LiveQuote } from "@/lib/api";

type LiveMap = Record<string, LiveQuote>;
const LiveContext = createContext<{ quotes: LiveMap; connected: boolean }>({ quotes: {}, connected: false });
export const useLive = () => useContext(LiveContext);

/** One shared Server-Sent Events connection for the whole app, with polling fallback. */
function LiveProvider({ children }: { children: React.ReactNode }) {
  const [quotes, setQuotes] = useState<LiveMap>({});
  const [connected, setConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const apply = (rows: LiveQuote[]) => setQuotes(Object.fromEntries(rows.map((r) => [r.asset_id, r])));
    let es: EventSource | null = null;
    const startPolling = () => {
      if (pollRef.current) return;
      const tick = () => api<LiveQuote[]>("/live").then(apply).catch(() => {});
      tick();
      pollRef.current = setInterval(tick, 30_000);
    };
    try {
      es = new EventSource(`${API_URL}/stream/live`);
      es.addEventListener("prices", (e) => apply(JSON.parse((e as MessageEvent).data)));
      es.onopen = () => setConnected(true);
      es.onerror = () => {
        setConnected(false);
        startPolling();
      };
    } catch {
      startPolling();
    }
    return () => {
      es?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return <LiveContext.Provider value={{ quotes, connected }}>{children}</LiveContext.Provider>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 } } }),
  );
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <QueryClientProvider client={qc}>
        <LiveProvider>{children}</LiveProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
