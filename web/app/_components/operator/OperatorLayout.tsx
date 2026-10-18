import { Suspense, type ReactNode } from "react";
import { OperatorKeyProvider } from "./OperatorKey";

type Props = { hint: string; keyParam?: string; children: ReactNode };

export function OperatorLayout({ hint, keyParam, children }: Props) {
  return (
    <div className="flex-1 bg-white text-gray-900">
      <Suspense>
        <OperatorKeyProvider hint={hint} keyParam={keyParam}>
          {children}
        </OperatorKeyProvider>
      </Suspense>
    </div>
  );
}
