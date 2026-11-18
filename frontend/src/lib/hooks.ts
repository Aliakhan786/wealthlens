"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type AssetSummary, type Metrics } from "./api";

export function useAssets() {
  return useQuery({
    queryKey: ["assets"],
    queryFn: () => api<AssetSummary[]>("/assets"),
    refetchInterval: 60_000,
  });
}

export function useMetrics(id: string) {
  return useQuery({ queryKey: ["metrics", id], queryFn: () => api<Metrics>(`/assets/${id}/metrics`), enabled: !!id });
}

export function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}
