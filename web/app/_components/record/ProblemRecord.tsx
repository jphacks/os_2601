import type { HintSource, ProblemStatus, SessionDetail, Trigger, Verdict } from "@/lib/api";
import { dateTime } from "./format";

type Problem = SessionDetail["problems"][number];
type Hint = Problem["hints"][number];

const STATUS_LABELS: Record<ProblemStatus, string> = {
  pending: "まだ",
  working: "途中",
  done: "できた",
  skipped: "飛ばした",
};
const TRIGGER_LABELS: Record<Trigger, string> = { auto: "手が止まって", manual: "ヒントボタン", voice: "声で呼んだ" };
const SOURCE_LABELS: Record<HintSource, string> = { gpt: "AI", fallback: "固定の問い返し", scripted: "台本" };
const VERDICT_LABELS: Record<Verdict, string> = { correct: "正解", incorrect: "不正解", unreadable: "読めなかった" };

function duration(seconds: number): string {
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}

function HintRow({ hint }: { hint: Hint }) {
  const byAi = hint.source === "gpt";
  return (
    <li className={`flex flex-col gap-1 rounded border-l-4 px-3 py-2 ${byAi ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
        <span>{dateTime(hint.created_at)}</span>
        <span>{TRIGGER_LABELS[hint.trigger]}</span>
        <span>段階 {hint.level}</span>
        {byAi && <span className="rounded bg-amber-100 px-2 text-amber-900">{hint.stuck_point}</span>}
        <span className={byAi ? "font-bold text-blue-700" : ""}>
          {SOURCE_LABELS[hint.source]}
          {byAi && `・待ち ${(hint.latency_ms / 1000).toFixed(1)} 秒`}
        </span>
        {!hint.leak_check.ok && <span className="rounded bg-red-100 px-2 text-red-800">答えに近い文を止めて差し替えた</span>}
      </div>
      <p>{hint.display}</p>
    </li>
  );
}

export function ProblemRecord({ problem }: { problem: Problem }) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-gray-200 p-4">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h3 className="text-lg font-bold">{problem.problem_no} 問目</h3>
        {problem.problem_text && <span className="font-mono">{problem.problem_text}</span>}
        <span className="ml-auto text-sm text-gray-600">
          {STATUS_LABELS[problem.status]}・詰まった {problem.stuck_count} 回・{duration(problem.seconds_spent)}
        </span>
      </header>
      {problem.hints.length > 0 && (
        <ol className="flex flex-col gap-2">
          {problem.hints.map((hint) => (
            <HintRow key={hint.hint_id} hint={hint} />
          ))}
        </ol>
      )}
      {problem.check && (
        <p className="text-sm">
          <span className="font-bold">できた：{VERDICT_LABELS[problem.check.verdict]}</span>　{problem.check.display}
        </p>
      )}
    </section>
  );
}
