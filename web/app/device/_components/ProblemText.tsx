// AI が答案の写真から読み取った問題文。まだ読み取っていなければ何も出さない
export function ProblemText({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <p className="max-w-full rounded-full bg-white px-5 py-2 text-center font-mono text-base font-bold break-words text-slate-800 shadow-sm">
      {text}
    </p>
  );
}
