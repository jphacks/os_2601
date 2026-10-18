import type { SessionDetail } from "@/lib/api";
import { ProblemRecord } from "./ProblemRecord";
import { StuckPointBars } from "./StuckPointBars";

export function SessionRecord({ session }: { session: SessionDetail }) {
  return (
    <>
      <dl className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-gray-50 p-3">
          <dt className="text-sm text-gray-600">できた問題</dt>
          <dd className="text-2xl font-bold">{session.problems.filter((problem) => problem.status === "done").length}</dd>
        </div>
        <div className="rounded-lg bg-gray-50 p-3">
          <dt className="text-sm text-gray-600">詰まった回数</dt>
          <dd className="text-2xl font-bold">{session.problems.reduce((total, problem) => total + problem.stuck_count, 0)}</dd>
        </div>
        <div className="rounded-lg bg-gray-50 p-3">
          <dt className="text-sm text-gray-600">答えを言いそうになって止めた回数</dt>
          <dd className="text-2xl font-bold">{session.leak_blocked_count}</dd>
        </div>
      </dl>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold">どこで詰まったか</h2>
        <StuckPointBars points={session.stuck_points} />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold">問題ごと</h2>
        {session.problems
          .filter((problem) => problem.status !== "pending")
          .map((problem) => (
            <ProblemRecord key={problem.problem_no} problem={problem} />
          ))}
      </section>
    </>
  );
}
