"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getSession, type SessionDetail, type State } from "@/lib/api";
import { startCamera } from "@/lib/camera";
import { startSession } from "@/lib/loop";
import { unlockSpeech } from "@/lib/speech";
import { Caption } from "./_components/Caption";
import { Header } from "./_components/Header";
import { StateBadge } from "./_components/StateBadge";
import { VideoFrame } from "./_components/VideoFrame";

// docs/06 の「状態と表示」で字幕が固定の状態
const FIXED_CAPTIONS: Partial<Record<State, string>> = {
  created: "スマホを立てて、手元が映るようにしてね",
  checking: "見てるよ…",
  ended: "今日はここまで。記録を見てみよう",
};

function Device() {
  const params = useSearchParams();
  const sessionId = params.get("s") ?? "";
  const token = params.get("t") ?? "";

  const videoRef = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<(() => void) | null>(null);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [state, setState] = useState<State>("created");
  const [problemNo, setProblemNo] = useState(1);
  const [caption, setCaption] = useState(FIXED_CAPTIONS.created ?? "");

  useEffect(() => {
    if (!sessionId || !token) return;
    let cancelled = false;
    getSession(sessionId, { token })
      .then((detail) => {
        if (cancelled) return;
        setSession(detail);
        setProblemNo(detail.current_problem_no);
      })
      .catch((error) => console.warn("[device] getSession に失敗", error));
    return () => {
      cancelled = true;
    };
  }, [sessionId, token]);

  useEffect(() => () => stopRef.current?.(), []);

  // 仮のボタン。本物の「はじめる」は次の部品（Buttons）で作る
  async function handleStart() {
    const video = videoRef.current;
    if (!video || stopRef.current) return;
    unlockSpeech();
    try {
      await startCamera(video);
    } catch (error) {
      console.warn("[device] startCamera に失敗", error);
      return;
    }
    stopRef.current = startSession(video, sessionId, token, {
      onState: (signal) => {
        setState(signal.state);
        setProblemNo(signal.current_problem_no);
        const fixed = FIXED_CAPTIONS[signal.state];
        if (fixed) setCaption(fixed);
      },
      onHint: (hint) => {
        if (hint.display) setCaption(hint.display);
      },
      onBrightness: () => {},
      onConnection: () => {},
      onHeard: () => {},
    });
  }

  return (
    <main className="flex flex-1 flex-col">
      {session && (
        <Header
          worksheetId={session.worksheet_id}
          worksheetTitle={session.worksheet_title}
          problemNo={problemNo}
          problemCount={session.problem_count}
        />
      )}
      <VideoFrame videoRef={videoRef}>
        <StateBadge state={state} />
      </VideoFrame>
      <div className="flex flex-col gap-4 p-4">
        <Caption text={caption} />
        <button
          type="button"
          onClick={handleStart}
          disabled={state !== "created"}
          className="min-h-14 rounded-lg bg-blue-600 px-6 text-lg font-bold text-white disabled:opacity-40"
        >
          はじめる
        </button>
      </div>
    </main>
  );
}

export default function DevicePage() {
  return (
    <Suspense>
      <Device />
    </Suspense>
  );
}
