"use client";

import Link from "next/link";
import { useCallback } from "react";
import { useParams } from "next/navigation";
import { getSession } from "@/lib/api";
import { ProblemRecord } from "../_components/ProblemRecord";
import { StuckPointBars } from "../_components/StuckPointBars";
import { useOperatorPolling } from "../_components/useOperatorPolling";
import { dateTime, sessionStatus } from "../format";

export default function LogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const load = useCallback((operatorKey: string) => getSession(id, { operatorKey }), [id]);
  const { data: session, error } = useOperatorPolling(load);
  const touched = session?.problems.filter((problem) => problem.status !== "pending") ?? [];

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <Link href="/log" className="text-sm text-blue-700">
        ← 一覧
      </Link>
      {error && <p className="text-red-700">{error}</p>}
      {session && (
        <>
          <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 className="text-2xl font-bold">{session.learner_label} の記録</h1>
            <span className="text-gray-500">
              {dateTime(session.created_at)}・{sessionStatus(session.state)}
            </span>
            {session.mode === "scripted" && <span className="rounded bg-gray-200 px-2 text-sm">台本</span>}
          </header>
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
            {touched.map((problem) => (
              <ProblemRecord key={problem.problem_no} problem={problem} />
            ))}
          </section>
        </>
      )}
    </main>
  );
}
