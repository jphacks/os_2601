export function ProblemText({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <p className="ml-1 max-w-full self-start rounded-full bg-white px-5 py-2 font-mono text-base font-bold break-words text-slate-800 shadow-sm">
      {text}
    </p>
  );
}
