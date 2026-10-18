"use client";

import { Suspense } from "react";
import { OperatorKeyProvider } from "./_components/OperatorKey";

export default function LogLayout({ children }: LayoutProps<"/log">) {
  return (
    <div className="flex-1 bg-white text-gray-900">
      <Suspense>
        <OperatorKeyProvider>{children}</OperatorKeyProvider>
      </Suspense>
    </div>
  );
}
