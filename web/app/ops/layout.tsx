import { Suspense } from "react";
import { OperatorKeyProvider } from "@/app/_components/operator/OperatorKey";

export default function OpsLayout({ children }: LayoutProps<"/ops">) {
  return (
    <div className="flex-1 bg-white text-gray-900">
      <Suspense>
        <OperatorKeyProvider>{children}</OperatorKeyProvider>
      </Suspense>
    </div>
  );
}
