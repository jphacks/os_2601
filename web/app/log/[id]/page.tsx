"use client";

import Link from "next/link";
import { useCallback } from "react";
import { useParams } from "next/navigation";
import { getSession } from "@/lib/api";
import { dateTime, sessionStatus } from "@/app/_components/record/format";
import { SessionRecord } from "@/app/_components/record/SessionRecord";
import { useOperatorPolling } from "@/app/_components/operator/useOperatorPolling";

export default function LogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const load = useCallback((operatorKey: string) => getSession(id, { operatorKey }), [id]);
  const { data: session, error } = useOperatorPolling(load);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <Link href="/log" className="text-sm text-blue-700">
        ← 一覧
      </Link>
      {error && <p className="text-red-700">{error}</p>}
      {session && (
        <>
          <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 className="text-2xl font-bold">記録：{session.learner_label}</h1>
            <span className="text-gray-500">
              {dateTime(session.created_at)}・{sessionStatus(session.state)}
            </span>
            {session.mode === "scripted" && <span className="rounded bg-gray-200 px-2 text-sm">台本</span>}
          </header>
          <SessionRecord session={session} />
        </>
      )}
    </main>
  );
}
