"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const OperatorKeyContext = createContext("");

export function useOperatorKey(): string {
  return useContext(OperatorKeyContext);
}

type Props = { hint: string; keyParam?: string; children: ReactNode };

export function OperatorKeyProvider({ hint, keyParam, children }: Props) {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const [operatorKey, setOperatorKey] = useState(() => (keyParam && params.get(keyParam)) || "");

  useEffect(() => {
    if (keyParam && params.has(keyParam)) router.replace(pathname, { scroll: false });
  }, [keyParam, params, pathname, router]);

  return (
    <OperatorKeyContext value={operatorKey}>
      {!operatorKey && (
        <p className="px-6 pt-4 text-sm text-gray-700">{hint}</p>
      )}
      <label className="flex flex-wrap items-center gap-2 px-6 pt-4 text-sm text-gray-500">
        <span>X-Operator-Key</span>
        <input
          type="password"
          autoComplete="off"
          value={operatorKey}
          onChange={(event) => setOperatorKey(event.target.value)}
          className="w-56 max-w-full rounded border border-gray-300 px-2 py-0.5"
        />
      </label>
      {children}
    </OperatorKeyContext>
  );
}
