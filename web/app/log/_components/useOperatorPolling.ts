"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { useOperatorKey } from "./OperatorKey";

const REFRESH_MS = 2000;
const TIMEOUT_MS = 5000;

type Load<T> = (operatorKey: string) => Promise<T>;
type Polled<T> = { load: Load<T>; operatorKey: string; data: T | null; error: string };

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) return "鍵が違います";
  return error instanceof Error ? error.message : String(error);
}

export function useOperatorPolling<T>(load: Load<T>): { data: T | null; error: string } {
  const operatorKey = useOperatorKey();
  const [polled, setPolled] = useState<Polled<T> | null>(null);

  useEffect(() => {
    if (!operatorKey) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const data = await Promise.race([
          load(operatorKey),
          new Promise<never>((_, reject) => setTimeout(() => reject(new Error("つながりにくいみたい")), TIMEOUT_MS)),
        ]);
        if (!cancelled) setPolled({ load, operatorKey, data, error: "" });
      } catch (caught) {
        if (!cancelled)
          setPolled((previous) => ({
            load,
            operatorKey,
            data: previous?.load === load && previous.operatorKey === operatorKey ? previous.data : null,
            error: errorText(caught),
          }));
      }
      if (!cancelled) timer = setTimeout(refresh, REFRESH_MS);
    }
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [operatorKey, load]);

  return polled?.load === load && polled.operatorKey === operatorKey ? polled : { data: null, error: "" };
}
