import { OperatorLayout } from "@/app/_components/operator/OperatorLayout";

const HINT = "運営用の画面です。運営の鍵を入れてください。セッションの作成とリセットができます。";

export default function OpsLayout({ children }: LayoutProps<"/ops">) {
  return <OperatorLayout hint={HINT}>{children}</OperatorLayout>;
}
