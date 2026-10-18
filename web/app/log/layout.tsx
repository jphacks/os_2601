import { OperatorLayout } from "@/app/_components/operator/OperatorLayout";

const HINT = "運営用の画面です。運営の鍵を入れてください。学習者の記録は、/device の「おわる」→「記録を見る」で見られます。";

export default function LogLayout({ children }: LayoutProps<"/log">) {
  return (
    <OperatorLayout hint={HINT} keyParam="k">
      {children}
    </OperatorLayout>
  );
}
