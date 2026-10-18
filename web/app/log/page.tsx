"use client";

import Link from "next/link";
import { listSessions } from "@/lib/api";
import { clock, sessionStatus } from "./_components/format";
import { usePolled } from "./_components/usePolled";

export default function LogListPage() {
  const { data, error } = usePolled(listSessions);
  const sessions = [...(data?.sessions ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at));

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-4 p-6">
      <h1 className="text-2xl font-bold">となりの記録</h1>
      {error && <p className="text-red-700">{error}</p>}
      {data && sessions.length === 0 && <p className="text-gray-500">まだ記録がありません</p>}
      <ul className="flex flex-col gap-2">
        {sessions.map((session) => (
          <li key={session.session_id}>
            <Link
              href={`/log/${session.session_id}`}
              className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-lg border border-gray-200 px-4 py-3 hover:bg-gray-50"
            >
              <span className="font-bold">{session.learner_label}</span>
              <span className="text-gray-500">{clock(session.created_at)}</span>
              <span className="text-gray-500">{sessionStatus(session.state)}</span>
              <span className="ml-auto">
                できた {session.problem_done} 問・詰まった {session.stuck_total} 回
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
