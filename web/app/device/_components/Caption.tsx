// 字幕は となり の吹き出しとして出す。文字は display をそのまま、等幅（18px）
export function Caption({ text }: { text: string }) {
  return (
    <p className="min-h-[3em] rounded-3xl rounded-bl-md bg-white px-5 py-4 font-mono text-lg leading-relaxed break-words text-slate-800 shadow-md">
      {text}
    </p>
  );
}

// 学習者の声として聞き取った文字。吹き出しを右に寄せて、となり の字幕と区別する
export function HeardBubble({ text }: { text: string }) {
  return (
    <p className="self-end rounded-3xl rounded-br-md bg-sky-100 px-4 py-2 text-sm text-slate-600 shadow-sm">
      聞こえた：{text}
    </p>
  );
}
