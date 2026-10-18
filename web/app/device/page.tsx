"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, getSession, openSession, patchSettings, type SessionDetail, type State } from "@/lib/api";
import { startCamera, stopCamera } from "@/lib/camera";
import { advance, end, requestCheck, requestManualHint, startSession, updateSessionPersona } from "@/lib/loop";
import { endMessage } from "@/lib/personas";
import { setSpeechCharacter, speak, stopSpeaking, unlockSpeech } from "@/lib/speech";
import { primeListening, stopListening, voiceStatus } from "@/lib/voice";
import { Buttons } from "./_components/Buttons";
import { Caption, HeardBubble } from "./_components/Caption";
import { Character } from "./_components/Character";
import { CharacterPicker } from "./_components/CharacterPicker";
import { Header } from "./_components/Header";
import { RecordSheet } from "./_components/RecordSheet";
import { nearestChoice, SecondsPicker } from "./_components/SecondsPicker";
import { ProblemText } from "./_components/ProblemText";
import { VideoFrame } from "./_components/VideoFrame";

// docs/06 の「状態と表示」で字幕が固定の状態
const FIXED_CAPTIONS: Partial<Record<State, string>> = {
  created: "スマホを立てて、手元が映るようにしてね",
  checking: "見てるよ…",
};
const CAMERA_DENIED_CAPTION = "設定からカメラを許可してね。LINE などの中のブラウザなら Safari か Chrome で開いてね";
const NO_SESSION_CAPTION = "セッションの URL から開いてね";
const END_CONFIRM = "おわる？";
// 平均輝度がこれ未満なら「明るさが足りません」を重ねる（docs/tasks/b.md の B1-4）
const DARK_BRIGHTNESS = 60;
// 聞き取った文字を字幕の下に出しておく時間（docs/06 の「声のトリガー」）
const HEARD_MS = 3000;

// ApiError は画面に何も出さない。それ以外はコンソールにだけ残す
function ignoreError(error: unknown) {
  if (!(error instanceof ApiError)) console.warn("[device] 操作に失敗", error);
}

function Device() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("s") ?? "";
  const token = params.get("t") ?? "";
  const debug = params.get("debug") === "1";

  const videoRef = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<(() => void) | null>(null);
  const startingRef = useRef(false);
  const sessionRef = useRef<SessionDetail | null>(null);
  const requestVersion = useRef(0);
  const stateRef = useRef<State>("created");
  const problemNoRef = useRef(1);
  const endSpokenRef = useRef(false);
  const personaUpdatingRef = useRef(false);
  const recordLoadingRef = useRef(false);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [record, setRecord] = useState<SessionDetail | null>(null);
  const [recordStatus, setRecordStatus] = useState<"idle" | "loading" | "failed">("idle");
  const [state, setState] = useState<State>("created");
  const [problemNo, setProblemNo] = useState(1);
  const [problemText, setProblemText] = useState<string | null>(null);
  const [caption, setCaption] = useState(FIXED_CAPTIONS.created ?? "");
  const [stuckSeconds, setStuckSeconds] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [personaUpdating, setPersonaUpdating] = useState(false);
  const [personaError, setPersonaError] = useState("");
  const [brightness, setBrightness] = useState<number | null>(null);
  const [stillSeconds, setStillSeconds] = useState(0);
  const [connected, setConnected] = useState(true);
  // 同じ文字が続けて来ても 3 秒を数え直すように、受け取るたびに新しいオブジェクトにする
  const [heard, setHeard] = useState<{ text: string } | null>(null);

  useEffect(() => {
    if (sessionId && token) return;
    let cancelled = false;
    openSession()
      .then((created) => {
        if (cancelled) return;
        const query = new URLSearchParams({ s: created.session_id, t: created.session_token });
        if (debug) query.set("debug", "1");
        router.replace(`/device?${query}`);
      })
      .catch((error) => {
        if (cancelled) return;
        ignoreError(error);
        setCaption(NO_SESSION_CAPTION);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, token, debug, router]);

  useEffect(() => {
    if (!sessionId || !token) return;
    let cancelled = false;
    const version = ++requestVersion.current;
    getSession(sessionId, { token })
      .then((detail) => {
        if (cancelled || version !== requestVersion.current) return;
        const initialState = detail.state === "ended" ? "ended" : "created";
        sessionRef.current = detail;
        setSpeechCharacter(detail.settings.persona === "ikemen" ? "handsome" : "teacher");
        stateRef.current = initialState;
        problemNoRef.current = detail.current_problem_no;
        endSpokenRef.current = initialState === "ended";
        personaUpdatingRef.current = false;
        startingRef.current = false;
        recordLoadingRef.current = false;
        setSession(detail);
        setRecord(null);
        setRecordStatus("idle");
        setState(initialState);
        setCaption(initialState === "ended"
          ? endMessage(detail.settings.persona, detail.persona_options)
          : FIXED_CAPTIONS.created ?? "");
        setBusy(false);
        setPersonaUpdating(false);
        setPersonaError("");
        setProblemNo(detail.current_problem_no);
        setProblemText(detail.problems[detail.current_problem_no - 1]?.problem_text ?? null);
      })
      .catch((error) => {
        console.warn("[device] getSession に失敗", error);
        if (!cancelled) setConnected(false);
      });
    return () => {
      cancelled = true;
      requestVersion.current += 1;
      sessionRef.current = null;
      stopRef.current?.();
      stopRef.current = null;
      stopCamera();
      stopSpeaking();
    };
  }, [sessionId, token]);

  useEffect(
    () => () => {
      stopRef.current?.();
      stopCamera();
      stopSpeaking();
    },
    [],
  );

  useEffect(() => {
    if (!heard) return;
    const timer = setTimeout(() => setHeard(null), HEARD_MS);
    return () => clearTimeout(timer);
  }, [heard]);

  function applyState(next: State, nextProblemNo: number) {
    // startSessionのコールバックは最初の描画を保持するため、現在の番号はrefで比較する。
    // 次へ進んだ後に届いた古い応答で、前の問題文を復活させない。
    // 再開直後のloopはまだ問題番号1を持つ場合がある。終了はセッション全体に適用する。
    const appliedProblemNo = next === "ended" ? Math.max(problemNoRef.current, nextProblemNo) : nextProblemNo;
    if (appliedProblemNo < problemNoRef.current || (stateRef.current === "ended" && next !== "ended")) return;
    if (appliedProblemNo !== problemNoRef.current) setProblemText(null);
    problemNoRef.current = appliedProblemNo;
    stateRef.current = next;
    setState(next);
    setProblemNo(appliedProblemNo);
    if (next === "ended") {
      const confirmed = sessionRef.current;
      const persona = confirmed?.settings.persona ?? "teacher";
      const message = endMessage(persona, confirmed?.persona_options);
      setCaption(message);
      if (!endSpokenRef.current) {
        endSpokenRef.current = true;
        stopListening();
        stopSpeaking();
        void speak(message).catch((error) => console.warn("[device] 終了の読み上げに失敗", error));
      }
      return;
    }
    const fixed = FIXED_CAPTIONS[next];
    if (fixed) setCaption(fixed);
  }

  const defaultSeconds = session ? nearestChoice(session.settings.stuck_seconds) : null;
  const selectedSeconds = stuckSeconds ?? defaultSeconds;
  const selectedPersona = session?.settings.persona ?? "teacher";
  // 絵と話し方は、サーバーで保存が確認できた同じ人格にそろえる。
  const characterId = selectedPersona === "ikemen" ? "handsome" : "teacher";
  const canChangePersona = ["created", "watching", "still", "cooldown"].includes(state);

  async function handlePersonaChange(value: string) {
    if (
      (value !== "teacher" && value !== "ikemen") || personaUpdatingRef.current || startingRef.current || busy ||
      !["created", "watching", "still", "cooldown"].includes(stateRef.current)
    ) return;
    const confirmed = sessionRef.current;
    if (!confirmed || confirmed.settings.persona === value) return;
    const version = requestVersion.current;
    personaUpdatingRef.current = true;
    setPersonaUpdating(true);
    setPersonaError("");
    try {
      const response = await patchSettings(sessionId, token, { persona: value });
      if (version !== requestVersion.current || stateRef.current === "ended" || !sessionRef.current) return;
      const next = { ...sessionRef.current, settings: response.settings };
      sessionRef.current = next;
      setSession(next);
      setSpeechCharacter(response.settings.persona === "ikemen" ? "handsome" : "teacher");
      updateSessionPersona(sessionId, response.settings.persona);
    } catch (error) {
      if (version === requestVersion.current && stateRef.current !== "ended") {
        setPersonaError("切り替えられませんでした。もう一度試してね。");
        ignoreError(error);
      }
    } finally {
      if (version === requestVersion.current) {
        personaUpdatingRef.current = false;
        setPersonaUpdating(false);
      }
    }
  }

  async function handleStart() {
    const video = videoRef.current;
    // 連打で startCamera と startSession が 2 回走らないようにする（state の busy は再描画まで効かない）
    if (
      !video || !sessionRef.current || stopRef.current || startingRef.current || personaUpdatingRef.current ||
      stateRef.current !== "created"
    ) return;
    const version = requestVersion.current;
    startingRef.current = true;
    setBusy(true);
    // patchSettings は先に送り出すが、await は unlockSpeech の後にする（クリック直後でないと iOS で音が出ない）
    // 学習者が選んだときだけ送る。選択肢に無い秒数（/ops で 12 秒など）を一番近い選択肢で上書きしない
    const patching =
      stuckSeconds !== null && stuckSeconds !== session?.settings.stuck_seconds
        ? patchSettings(sessionId, token, { stuck_seconds: stuckSeconds }).catch(ignoreError)
        : null;
    setSpeechCharacter(characterId);
    unlockSpeech();
    primeListening();
    try {
      await startCamera(video);
    } catch (error) {
      if (version !== requestVersion.current) return;
      console.warn("[device] startCamera に失敗", error);
      stopListening();
      setCaption(CAMERA_DENIED_CAPTION);
      setBusy(false);
      startingRef.current = false;
      return;
    }
    const updated = await patching;
    if (version !== requestVersion.current || !sessionRef.current) {
      stopCamera();
      return;
    }
    if (updated) {
      sessionRef.current = { ...sessionRef.current, settings: updated.settings };
      setSession(sessionRef.current);
      setSpeechCharacter(updated.settings.persona === "ikemen" ? "handsome" : "teacher");
    }
    endSpokenRef.current = false;
    stopRef.current = startSession(video, sessionId, token, {
      onState: (signal) => {
        if (
          version !== requestVersion.current ||
          (signal.state !== "ended" && signal.current_problem_no < problemNoRef.current)
        ) return;
        applyState(signal.state, signal.current_problem_no);
        setStillSeconds(signal.still_seconds);
      },
      onHint: (hint) => {
        if (
          version !== requestVersion.current || stateRef.current === "ended" ||
          hint.problem_no !== problemNoRef.current
        ) return;
        if (hint.speech !== null) setCaption(hint.display);
        setProblemText(hint.problem_text);
      },
      onBrightness: setBrightness,
      onConnection: setConnected,
      onHeard: (text) => setHeard({ text }),
      onProblem: (text) => {
        if (version === requestVersion.current && stateRef.current !== "ended") setProblemText(text);
      },
    }, sessionRef.current.settings.persona);
    setBusy(false);
    startingRef.current = false;
  }

  async function handleHint() {
    const version = requestVersion.current;
    setBusy(true);
    try {
      const hint = await requestManualHint();
      if (
        version !== requestVersion.current || stateRef.current === "ended" ||
        hint.problem_no !== problemNoRef.current
      ) return;
      if (hint.speech !== null) setCaption(hint.display);
      setProblemText(hint.problem_text);
      applyState(hint.state, hint.problem_no);
    } catch (error) {
      if (version === requestVersion.current) ignoreError(error);
    } finally {
      if (version === requestVersion.current) setBusy(false);
    }
  }

  async function handleCheck() {
    const version = requestVersion.current;
    const checkedProblemNo = problemNoRef.current;
    const before = { state, problemNo, caption };
    setBusy(true);
    applyState("checking", problemNo);
    try {
      const check = await requestCheck();
      if (version !== requestVersion.current || checkedProblemNo !== problemNoRef.current || stateRef.current === "ended") return;
      applyState(check.state, check.next_problem_no ?? check.problem_no);
      if (check.state !== "ended" && !FIXED_CAPTIONS[check.state]) setCaption(check.display);
    } catch (error) {
      if (version === requestVersion.current && checkedProblemNo === problemNoRef.current && stateRef.current !== "ended") {
        ignoreError(error);
        stateRef.current = before.state;
        setState(before.state);
        setCaption(before.caption);
      }
    } finally {
      if (version === requestVersion.current) setBusy(false);
    }
  }

  async function handleNext() {
    const version = requestVersion.current;
    setBusy(true);
    try {
      const response = await advance();
      if (version !== requestVersion.current || response.current_problem_no < problemNoRef.current) return;
      applyState(response.state, response.current_problem_no);
    } catch (error) {
      if (version === requestVersion.current) ignoreError(error);
    } finally {
      if (version === requestVersion.current) setBusy(false);
    }
  }

  async function handleEnd() {
    if (personaUpdatingRef.current || startingRef.current || stateRef.current === "ended") return;
    if (!window.confirm(END_CONFIRM)) return;
    const version = requestVersion.current;
    setBusy(true);
    try {
      await end();
    } catch (error) {
      if (version === requestVersion.current) ignoreError(error);
    } finally {
      if (version === requestVersion.current) {
        stopRef.current = null;
        setBusy(false);
      }
    }
  }

  async function handleShowRecord() {
    if (recordLoadingRef.current || stateRef.current !== "ended") return;
    const version = requestVersion.current;
    recordLoadingRef.current = true;
    setRecordStatus("loading");
    try {
      const latest = await getSession(sessionId, { token });
      if (version !== requestVersion.current || stateRef.current !== "ended") return;
      setRecord(latest);
      setRecordStatus("idle");
    } catch (error) {
      if (version === requestVersion.current) {
        ignoreError(error);
        setRecordStatus("failed");
      }
    } finally {
      if (version === requestVersion.current) recordLoadingRef.current = false;
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
        {/* 上：ヘッダと問題文を真ん中、映像は右上に小さく（映像は常に表示する。docs/06） */}
        <div className="flex items-start gap-3">
          <div className="flex min-w-0 flex-1 flex-col items-center gap-2">
            <Header mode={session?.mode ?? null} connected={connected} />
            <ProblemText text={problemText} />
          </div>
          <div className="flex w-28 shrink-0 flex-col gap-3">
            <VideoFrame
              videoRef={videoRef}
              dark={brightness !== null && brightness < DARK_BRIGHTNESS}
              debugText={debug ? `輝度 ${brightness === null ? "-" : Math.round(brightness)} / 静止 ${stillSeconds} 秒 / 声 ${voiceStatus()}` : null}
            />
            {state === "ended" && (
              <button
                type="button"
                onClick={handleShowRecord}
                disabled={recordStatus === "loading"}
                className="rounded-full bg-white px-3 py-2.5 text-sm font-bold text-sky-700 shadow-md ring-2 ring-sky-300 disabled:opacity-60"
              >
                {recordStatus === "loading" ? "読み込み中…" : "記録を見る"}
              </button>
            )}
            {recordStatus === "failed" && (
              <p className="rounded-lg bg-white/80 px-2 py-1 text-center text-xs font-bold text-red-700">記録を読めませんでした</p>
            )}
          </div>
        </div>
        {/* 真ん中：キャラクターを左下に大きく、吹き出しを右に重ねる（Tolan の会話画面の並び） */}
        <div className="relative flex min-h-80 flex-1 items-end">
          <Character state={state} id={characterId} className="absolute bottom-0 -left-4 h-[95%] max-h-[28rem] w-auto" />
          <div className="relative ml-[38%] flex w-[62%] flex-col gap-3 self-center">
            {heard && <HeardBubble text={heard.text} />}
            <Caption text={caption} />
          </div>
        </div>
        {/* 下：入力欄の位置にボタン */}
        <div className="relative flex flex-col gap-3 rounded-[2rem] bg-white/70 p-3 shadow-lg backdrop-blur">
          {state !== "ended" && <CharacterPicker
            value={characterId}
            onChange={(id) => void handlePersonaChange(id === "handsome" ? "ikemen" : "teacher")}
            disabled={!session || busy || personaUpdating || !canChangePersona}
          />}
          {personaError && <p role="status" className="px-2 text-sm text-red-700">{personaError}</p>}
          {state === "created" && selectedSeconds !== null && (
            <SecondsPicker value={selectedSeconds} onChange={setStuckSeconds} />
          )}
          <Buttons
            state={state}
            busy={busy || personaUpdating || !session}
            onStart={handleStart}
            onHint={handleHint}
            onCheck={handleCheck}
            onNext={handleNext}
            onEnd={handleEnd}
          />
        </div>
      </div>
      {record && <RecordSheet session={record} onClose={() => setRecord(null)} />}
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
