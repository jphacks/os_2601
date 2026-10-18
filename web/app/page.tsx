import Link from "next/link";

const PAGES = [
  { href: "/device", title: "となり（学習者）", text: "スマホで開いて「はじめる」を押すだけ。紙の問題を解く手元を映す" },
  { href: "/log", title: "記録（運営用）", text: "運営の鍵が要る。学習者は「おわる」→「記録を見る」で見られる" },
  { href: "/ops", title: "運営", text: "運営の鍵が要る。セッションの作成とリセット" },
];

export default function Home() {
  return (
    <main className="flex flex-1 justify-center bg-white text-gray-900">
      <div className="flex w-full max-w-xl flex-col gap-6 p-8">
        <div>
          <h1 className="text-3xl font-bold">となり</h1>
          <p className="mt-2 text-gray-600">机の横で手元を見て、詰まったときだけ声をかける、答えを言わない AI 家庭教師。</p>
        </div>
        <ul className="flex flex-col gap-3">
          {PAGES.map((page) => (
            <li key={page.href}>
              <Link href={page.href} className="block rounded-lg border border-gray-200 px-4 py-3 hover:bg-gray-50">
                <span className="block font-bold">{page.title}</span>
                <span className="block text-sm text-gray-600">{page.text}</span>
              </Link>
            </li>
          ))}
        </ul>
        <a href="https://github.com/jphacks/os_2601" className="text-sm text-blue-700 underline">
          仕組みと既知の制約（README）
        </a>
        <p className="text-xs text-gray-500">声：VOICEVOX:青山龍星、VOICEVOX:冥鳴ひまり</p>
      </div>
    </main>
  );
}
