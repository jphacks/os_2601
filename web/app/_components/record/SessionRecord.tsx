import type { SessionDetail } from "@/lib/api";
import { ProblemRecord } from "./ProblemRecord";
import { StuckPointBars } from "./StuckPointBars";

export function SessionRecord({ session }: { session: SessionDetail }) {
  const recorded = session.problems.filter(
    (problem) => problem.stuck_count > 0 || problem.hints.length > 0 || problem.check !== null || problem.status === "skipped",
  );
  const totals = [
    { label: "できた問題", value: session.problems.filter((problem) => problem.status === "done").length },
    { label: "詰まった回数", value: session.problems.reduce((total, problem) => total + problem.stuck_count, 0) },
    { label: "答えを言いそうになって止めた回数", value: session.leak_blocked_count },
  ];
  return (
    <div className="flex flex-col gap-6">
      <dl className="grid grid-cols-3 gap-3 text-center">
        {totals.map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-gray-50 p-3">
            <dt className="text-sm text-gray-600">{label}</dt>
            <dd className="text-2xl font-bold">{value}</dd>
          </div>
        ))}
      </dl>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold">どこで詰まったか</h2>
        <StuckPointBars points={session.stuck_points} />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold">問題ごと</h2>
        {recorded.length === 0 && <p className="text-gray-500">まだありません</p>}
        {recorded.map((problem) => (
          <ProblemRecord key={problem.problem_no} problem={problem} />
        ))}
      </section>
    </div>
  );
}
