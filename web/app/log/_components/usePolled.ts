"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { useOperatorKey } from "./OperatorKey";

const REFRESH_MS = 2000;

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) return "鍵が違います";
  return error instanceof ApiError ? error.message : String(error);
}

export function usePolled<T>(load: (operatorKey: string) => Promise<T>): { data: T | null; error: string } {
  const operatorKey = useOperatorKey();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!operatorKey) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const loaded = await load(operatorKey);
        if (cancelled) return;
        setData(loaded);
        setError("");
      } catch (caught) {
        if (!cancelled) setError(errorText(caught));
      }
      if (!cancelled) timer = setTimeout(refresh, REFRESH_MS);
    }
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [operatorKey, load]);

  return { data, error };
}
