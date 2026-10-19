"use client";

import { useState, type FormEvent } from "react";
import { useOperatorKey } from "@/app/_components/operator/OperatorKey";
import { errorText, useOperatorPolling } from "@/app/_components/operator/useOperatorPolling";
import { createSession, demoReset, listSessions, postSignal, type Mode, type SessionCreated } from "@/lib/api";

const MODES: Mode[] = ["live", "scripted"];
// openapi.yaml の Settings の既定値
const DEFAULT_STUCK_SECONDS = 20;
const DEFAULT_COOLDOWN_SECONDS = 60;

const INPUT = "rounded border border-gray-400 px-2 py-1";
const BUTTON = "rounded bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-40";

export default function OpsPage() {
  const operatorKey = useOperatorKey();
  const { data: list, error: listError } = useOperatorPolling(listSessions);
  const [mode, setMode] = useState<Mode>("live");
  const [stuckSeconds, setStuckSeconds] = useState(DEFAULT_STUCK_SECONDS);
  const [cooldownSeconds, setCooldownSeconds] = useState(DEFAULT_COOLDOWN_SECONDS);
  const [created, setCreated] = useState<{ session: SessionCreated; link: string } | null>(null);
  const [stuckTarget, setStuckTarget] = useState("");
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setMessage("");
    try {
      const session = await createSession(
        { worksheet_id: "FREE", mode, settings: { stuck_seconds: stuckSeconds, cooldown_seconds: cooldownSeconds } },
        operatorKey,
      );
      const query = new URLSearchParams({ s: session.session_id, t: session.session_token });
      setCreated({ session, link: `${window.location.origin}/device?${query}` });
      setStuckTarget(session.session_id);
    } catch (error) {
      setMessage(`作成に失敗: ${errorText(error)}`);
    } finally {
      setCreating(false);
    }
  }

  async function handleReset() {
    if (!window.confirm("全セッションをリセットしますか？")) return;
    setMessage("");
    try {
      const result = await demoReset(operatorKey);
      setCreated(null);
      setMessage(`リセットした（${result.removed_sessions} 件）`);
    } catch (error) {
      setMessage(`リセットに失敗: ${errorText(error)}`);
    }
  }

  async function handleForceStuck() {
    setMessage("");
    try {
      await postSignal(stuckTarget, { operatorKey }, { force_stuck: true });
      setMessage(`強制 stuck を送った（${stuckTarget}）`);
    } catch (error) {
      setMessage(`強制 stuck に失敗: ${errorText(error)}`);
    }
  }

  return (
    <main className="flex flex-col gap-6 p-6">
      <h1 className="text-2xl font-bold">となり ops</h1>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold">セッション作成</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1">
            mode
            <select value={mode} onChange={(event) => setMode(event.target.value as Mode)} className={INPUT}>
              {MODES.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            stuck_seconds
            <input
              type="number"
              min={5}
              max={1200}
              value={stuckSeconds}
              onChange={(event) => setStuckSeconds(Number(event.target.value))}
              className={`${INPUT} w-24`}
            />
          </label>
          <label className="flex flex-col gap-1">
            cooldown_seconds
            <input
              type="number"
              min={0}
              max={300}
              value={cooldownSeconds}
              onChange={(event) => setCooldownSeconds(Number(event.target.value))}
              className={`${INPUT} w-24`}
            />
          </label>
          <button type="submit" disabled={!operatorKey || creating} className={BUTTON}>
            作成
          </button>
        </form>
        {created && (
          <p className="flex flex-col gap-1">
            <a href={created.link} target="_blank" rel="noreferrer" className="text-blue-700 underline">
              {created.session.session_id} を /device で開く
            </a>
            <code className="font-mono text-sm break-all select-all">{created.link}</code>
          </p>
        )}
      </section>

      <section className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1">
          session_id
          <input
            value={stuckTarget}
            onChange={(event) => setStuckTarget(event.target.value)}
            className={`${INPUT} w-56 max-w-full`}
          />
        </label>
        <button type="button" onClick={handleForceStuck} disabled={!operatorKey || !stuckTarget} className={BUTTON}>
          強制 stuck
        </button>
        <button type="button" onClick={handleReset} disabled={!operatorKey} className={`${BUTTON} bg-red-600`}>
          リセット
        </button>
      </section>

      {message && <p className="font-mono text-sm">{message}</p>}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-bold">セッション一覧</h2>
        {listError && <p className="font-mono text-sm text-red-700">一覧の取得に失敗: {listError}</p>}
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                {["session_id", "worksheet", "learner", "mode", "state", "進み", "stuck", "created_at"].map((label) => (
                  <th key={label} className="px-2 py-1">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(list?.sessions ?? []).map((row) => (
                <tr key={row.session_id} className="border-b font-mono">
                  <td className="px-2 py-1">{row.session_id}</td>
                  <td className="px-2 py-1">{row.worksheet_id}</td>
                  <td className="px-2 py-1">{row.learner_label}</td>
                  <td className="px-2 py-1">{row.mode}</td>
                  <td className="px-2 py-1">{row.state}</td>
                  <td className="px-2 py-1">
                    {row.problem_done} / {row.problem_count}
                  </td>
                  <td className="px-2 py-1">{row.stuck_total}</td>
                  <td className="px-2 py-1">{row.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
