import Image from "next/image";
import Link from "next/link";
import { CHARACTERS } from "@/app/_components/characters/characters";

const STEPS = [
  "スマホを立てて、手元の紙が映るようにする",
  "紙の問題を、いつもどおり解く",
  "手が止まったら、となりが声をかける。答えは言わない",
];

const LINK = "underline decoration-white/60 underline-offset-4 hover:decoration-white";

export default function Home() {
  return (
    <main className="relative isolate flex flex-1 flex-col overflow-hidden bg-linear-to-b from-sky-400 via-sky-200 to-cyan-100 text-slate-800">
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-1/2 -bottom-1/3 -z-10 h-1/2 rounded-[50%] bg-linear-to-b from-lime-300 to-green-600"
      />
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center gap-6 px-6 pt-10 pb-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <h1 className="text-5xl font-black tracking-wide text-white drop-shadow-md">となり</h1>
          <p className="max-w-xs text-lg leading-relaxed font-bold text-slate-700">
            手が止まったときだけ、
            <br />
            答えを言わずに声をかける
            <br />
            AI 家庭教師
          </p>
        </div>

        <div className="relative flex h-56 w-full max-w-sm items-end justify-center gap-2">
          {CHARACTERS.map((character) => (
            <Image
              key={character.id}
              src={character.image}
              alt={character.label}
              priority
              className="h-full w-auto object-contain object-bottom drop-shadow-xl"
            />
          ))}
        </div>

        <Link
          href="/device"
          className="w-full max-w-sm rounded-full bg-sky-500 px-6 py-4 text-xl font-bold text-white shadow-lg transition active:scale-95"
        >
          はじめる
        </Link>

        <ol className="flex w-full max-w-sm flex-col gap-2 rounded-3xl bg-white/80 p-5 text-left shadow-md backdrop-blur">
          {STEPS.map((step, index) => (
            <li key={step} className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-500 text-sm font-bold text-white">
                {index + 1}
              </span>
              <span className="leading-7">{step}</span>
            </li>
          ))}
        </ol>

        <p className="max-w-sm text-xs leading-relaxed text-slate-700">
          カメラとマイクを使います。写真は、はじめたとき・手が止まりかけたとき・ボタンや声で呼んだときだけ Google の Gemini API に送ります。映像と声は残しません。
        </p>

        <footer className="mt-auto flex flex-col items-center gap-2 text-sm text-white drop-shadow">
          <nav className="flex flex-wrap justify-center gap-x-4 gap-y-1">
            <a href="https://github.com/jphacks/os_2601" className={LINK}>
              仕組みと既知の制約
            </a>
            <Link href="/log" className={LINK}>
              記録（運営用）
            </Link>
            <Link href="/ops" className={LINK}>
              運営
            </Link>
          </nav>
          <p className="text-xs">声：VOICEVOX:青山龍星、VOICEVOX:冥鳴ひまり</p>
        </footer>
      </div>
    </main>
  );
}
