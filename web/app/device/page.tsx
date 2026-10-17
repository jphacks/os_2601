"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, getSession, patchSettings, type SessionDetail, type State } from "@/lib/api";
import { startCamera, stopCamera } from "@/lib/camera";
import { advance, end, requestCheck, requestManualHint, startSession } from "@/lib/loop";
import { unlockSpeech } from "@/lib/speech";
import { Buttons } from "./_components/Buttons";
import { Caption, HeardBubble } from "./_components/Caption";
import { Character } from "./_components/Character";
import { CharacterPicker } from "./_components/CharacterPicker";
import { DEFAULT_CHARACTER, type CharacterId, type Mood } from "./_components/characters";
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
// 聞き取った文字を字幕の下に出しておく時間（docs/06 の「声のトリガー」）
const HEARD_MS = 3000;
// 表情を変えたら、次に変えるまで最低これだけ見せる（ころころ変わらないように）
const MOOD_HOLD_MS = 5000;

// 状態ごとの表情。stuck は心配、hint を話すときは楽しそうに、始まりと終わりは喜ぶ
const STATE_MOODS: Record<State, Mood> = {
  created: "joy",
  watching: "normal",
  still: "normal",
  stuck: "sad",
  speaking: "fun",
  cooldown: "normal",
  checking: "normal",
  ended: "joy",
};

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
  const [characterId, setCharacterId] = useState<CharacterId>(DEFAULT_CHARACTER);
  // check の結果（正解は喜、不正解・読めないは哀）。状態が変わるまで続ける
  const [verdictMood, setVerdictMood] = useState<Mood | null>(null);
  const [cameraDenied, setCameraDenied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [brightness, setBrightness] = useState<number | null>(null);
  const [stillSeconds, setStillSeconds] = useState(0);
  const [connected, setConnected] = useState(true);
  // 同じ文字が続けて来ても 3 秒を数え直すように、受け取るたびに新しいオブジェクトにする
  const [heard, setHeard] = useState<{ text: string } | null>(null);

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

  useEffect(() => {
    if (!heard) return;
    const timer = setTimeout(() => setHeard(null), HEARD_MS);
    return () => clearTimeout(timer);
  }, [heard]);

  function applyState(next: State, nextProblemNo: number) {
    setState(next);
    setVerdictMood(null);
    setProblemNo(nextProblemNo);
    const fixed = FIXED_CAPTIONS[next];
    if (fixed) setCaption(fixed);
  }

  // 見えない・つながらないときは怒り顔。それ以外は check の結果、なければ状態の表情
  const mood: Mood = cameraDenied || !connected ? "anger" : (verdictMood ?? STATE_MOODS[state]);

  const [shownMood, setShownMood] = useState<Mood>(mood);
  const shownAtRef = useRef(0);
  useEffect(() => {
    if (mood === shownMood) return;
    const wait = Math.max(0, shownAtRef.current + MOOD_HOLD_MS - Date.now());
    const timer = setTimeout(() => {
      shownAtRef.current = Date.now();
      setShownMood(mood);
    }, wait);
    return () => clearTimeout(timer);
  }, [mood, shownMood]);

  const defaultSeconds = session ? nearestChoice(session.settings.stuck_seconds) : null;
  const selectedSeconds = stuckSeconds ?? defaultSeconds;

  async function handleStart() {
    const video = videoRef.current;
    // 連打で startCamera と startSession が 2 回走らないようにする（state の busy は再描画まで効かない）
    if (!video || stopRef.current || startingRef.current) return;
    startingRef.current = true;
    setBusy(true);
    // patchSettings は先に送り出すが、await は unlockSpeech の後にする（クリック直後でないと iOS で音が出ない）
    // 学習者が選んだときだけ送る。選択肢に無い秒数（/ops で 12 秒など）を一番近い選択肢で上書きしない
    const patching =
      stuckSeconds !== null && stuckSeconds !== session?.settings.stuck_seconds
        ? patchSettings(sessionId, token, { stuck_seconds: stuckSeconds }).catch(ignoreError)
        : null;
    unlockSpeech();
    try {
      await startCamera(video);
      setCameraDenied(false);
    } catch (error) {
      console.warn("[device] startCamera に失敗", error);
      setCaption(CAMERA_DENIED_CAPTION);
      setCameraDenied(true);
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
      onHeard: (text) => setHeard({ text }),
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
      setVerdictMood(check.verdict === "correct" ? "joy" : "sad");
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
    <main className="relative isolate flex flex-1 flex-col overflow-hidden bg-linear-to-b from-sky-400 via-sky-200 to-cyan-100 text-slate-800">
      {/* 下の丘（飾り） */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-1/2 -bottom-1/3 -z-10 h-1/2 rounded-[50%] bg-linear-to-b from-lime-300 to-green-600"
      />
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-3 p-4">
        {/* 上：ヘッダとバッジを真ん中、映像は右上に小さく（映像は常に表示する。docs/06） */}
        <div className="flex items-start gap-3">
          <div className="flex min-w-0 flex-1 flex-col items-center gap-2">
            <Header
              info={
                session && {
                  worksheetId: session.worksheet_id,
                  worksheetTitle: session.worksheet_title,
                  problemNo,
                  problemCount: session.problem_count,
                  mode: session.mode,
                }
              }
              connected={connected}
            />
            <StateBadge state={state} />
          </div>
          <VideoFrame
            videoRef={videoRef}
            dark={brightness !== null && brightness < DARK_BRIGHTNESS}
            debugText={debug ? `輝度 ${brightness === null ? "-" : Math.round(brightness)} / 静止 ${stillSeconds} 秒` : null}
          />
        </div>
        {/* 真ん中：キャラクターを左下に大きく、吹き出しを右に重ねる（Tolan の会話画面の並び） */}
        <div className="relative flex min-h-[30rem] flex-1 items-end">
          <Character state={state} id={characterId} mood={shownMood} className="absolute bottom-0 -left-4 h-full max-h-[52rem] w-auto" />
          <div className="relative ml-[56%] flex w-[44%] flex-col gap-3 self-center">
            {heard && <HeardBubble text={heard.text} />}
            <Caption text={caption} />
          </div>
        </div>
        {/* 下：入力欄の位置にボタン */}
        <div className="relative flex flex-col gap-3 rounded-[2rem] bg-white/70 p-3 shadow-lg backdrop-blur">
          {state === "created" && <CharacterPicker value={characterId} onChange={setCharacterId} />}
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
