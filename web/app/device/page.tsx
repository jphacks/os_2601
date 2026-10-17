"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, getSession, patchSettings, type SessionDetail, type State } from "@/lib/api";
import { startCamera, stopCamera } from "@/lib/camera";
import { advance, end, requestCheck, requestManualHint, startSession } from "@/lib/loop";
import { unlockSpeech } from "@/lib/speech";
import { Buttons } from "./_components/Buttons";
import { Caption } from "./_components/Caption";
import { Header } from "./_components/Header";
import { nearestChoice, SecondsPicker } from "./_components/SecondsPicker";
import { StateBadge } from "./_components/StateBadge";
import { VideoFrame } from "./_components/VideoFrame";

// docs/06 の「状態と表示」で字幕が固定の状態
const FIXED_CAPTIONS: Partial<Record<State, string>> = {
  created: "スマホを立てて、手元が映るようにしてね",
  checking: "見てるよ…",
  ended: "今日はここまで。記録を見てみよう",
};
const CAMERA_DENIED_CAPTION = "設定からカメラを許可してね。LINE などの中のブラウザなら Safari か Chrome で開いてね";
const END_CONFIRM = "おわる？";
// 平均輝度がこれ未満なら「明るさが足りません」を重ねる（docs/tasks/b.md の B1-4）
const DARK_BRIGHTNESS = 60;

// ApiError は画面に何も出さない。それ以外はコンソールにだけ残す
function ignoreError(error: unknown) {
  if (!(error instanceof ApiError)) console.warn("[device] 操作に失敗", error);
}

function Device() {
  const params = useSearchParams();
  const sessionId = params.get("s") ?? "";
  const token = params.get("t") ?? "";
  const debug = params.get("debug") === "1";

  const videoRef = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<(() => void) | null>(null);
  const startingRef = useRef(false);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [state, setState] = useState<State>("created");
  const [problemNo, setProblemNo] = useState(1);
  const [caption, setCaption] = useState(FIXED_CAPTIONS.created ?? "");
  const [stuckSeconds, setStuckSeconds] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [brightness, setBrightness] = useState<number | null>(null);
  const [stillSeconds, setStillSeconds] = useState(0);
  const [connected, setConnected] = useState(true);

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

  useEffect(
    () => () => {
      stopRef.current?.();
      stopCamera();
    },
    [],
  );

  function applyState(next: State, nextProblemNo: number) {
    setState(next);
    setProblemNo(nextProblemNo);
    const fixed = FIXED_CAPTIONS[next];
    if (fixed) setCaption(fixed);
  }

  const defaultSeconds = session ? nearestChoice(session.settings.stuck_seconds) : null;
  const selectedSeconds = stuckSeconds ?? defaultSeconds;

  async function handleStart() {
    const video = videoRef.current;
    // 連打で startCamera と startSession が 2 回走らないようにする（state の busy は再描画まで効かない）
    if (!video || stopRef.current || startingRef.current) return;
    startingRef.current = true;
    setBusy(true);
    // patchSettings は先に送り出すが、await は unlockSpeech の後にする（クリック直後でないと iOS で音が出ない）
    const patching =
      selectedSeconds !== null && selectedSeconds !== session?.settings.stuck_seconds
        ? patchSettings(sessionId, token, { stuck_seconds: selectedSeconds }).catch(ignoreError)
        : null;
    unlockSpeech();
    try {
      await startCamera(video);
    } catch (error) {
      console.warn("[device] startCamera に失敗", error);
      setCaption(CAMERA_DENIED_CAPTION);
      setBusy(false);
      startingRef.current = false;
      return;
    }
    await patching;
    stopRef.current = startSession(video, sessionId, token, {
      onState: (signal) => {
        applyState(signal.state, signal.current_problem_no);
        setStillSeconds(signal.still_seconds);
      },
      onHint: (hint) => {
        if (hint.speech !== null) setCaption(hint.display);
      },
      onBrightness: setBrightness,
      onConnection: setConnected,
      onHeard: () => {},
    });
    setBusy(false);
    startingRef.current = false;
  }

  async function handleHint() {
    setBusy(true);
    try {
      const hint = await requestManualHint();
      if (hint.speech !== null) setCaption(hint.display);
      applyState(hint.state, hint.problem_no);
    } catch (error) {
      ignoreError(error);
    } finally {
      setBusy(false);
    }
  }

  async function handleCheck() {
    const before = { state, problemNo, caption };
    setBusy(true);
    applyState("checking", problemNo);
    try {
      const check = await requestCheck();
      applyState(check.state, check.next_problem_no ?? check.problem_no);
      if (!FIXED_CAPTIONS[check.state]) setCaption(check.display);
    } catch (error) {
      ignoreError(error);
      setState(before.state);
      setCaption(before.caption);
    } finally {
      setBusy(false);
    }
  }

  async function handleNext() {
    setBusy(true);
    try {
      const response = await advance();
      applyState(response.state, response.current_problem_no);
    } catch (error) {
      ignoreError(error);
    } finally {
      setBusy(false);
    }
  }

  async function handleEnd() {
    if (!window.confirm(END_CONFIRM)) return;
    setBusy(true);
    try {
      await end();
    } catch (error) {
      ignoreError(error);
    } finally {
      stopRef.current = null;
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col">
      {session && (
        <Header
          worksheetId={session.worksheet_id}
          worksheetTitle={session.worksheet_title}
          problemNo={problemNo}
          problemCount={session.problem_count}
          connected={connected}
        />
      )}
      <VideoFrame
        videoRef={videoRef}
        dark={brightness !== null && brightness < DARK_BRIGHTNESS}
        debugText={debug ? `輝度 ${brightness === null ? "-" : Math.round(brightness)} / 静止 ${stillSeconds} 秒` : null}
      >
        <StateBadge state={state} />
      </VideoFrame>
      <div className="flex flex-col gap-4 p-4">
        <Caption text={caption} />
        {state === "created" && selectedSeconds !== null && (
          <SecondsPicker value={selectedSeconds} onChange={setStuckSeconds} />
        )}
        <Buttons
          state={state}
          busy={busy}
          onStart={handleStart}
          onHint={handleHint}
          onCheck={handleCheck}
          onNext={handleNext}
          onEnd={handleEnd}
        />
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
