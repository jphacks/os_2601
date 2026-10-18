import {
  answerUtterance,
  postAdvance,
  postCheck,
  postEnd,
  postFrame,
  postSignal,
  readProblem,
  requestHint,
  type AdvanceResponse,
  type CheckResponse,
  type HintResponse,
  type SignalRequest,
  type SignalResponse,
  type State,
  type Trigger,
} from "./api";
import { captureFrame, stopCamera } from "./camera";
import { startMotionLoop } from "./motion";
import { normalizePersona, type Persona } from "./personas";
import { speak, stopSpeaking } from "./speech";
import { startListening, stopListening, voiceStatus } from "./voice";

export type SessionHandlers = {
  onState: (signal: SignalResponse) => void;
  onHint: (hint: HintResponse) => void;
  onBrightness: (brightness: number) => void;
  onConnection: (connected: boolean) => void;
  onHeard: (text: string) => void;
  onProblem: (text: string | null) => void;
};

type Session = {
  id: string;
  token: string;
  persona: Persona;
  handlers: SessionHandlers;
  running: boolean;
  state: State;
  problemNo: number;
  latestScore: number | null;
  cameraOk: boolean;
  signalInFlight: boolean;
  failedSignals: number;
  connected: boolean | null;
  greeted: boolean;
  requestInFlight: boolean;
  voiceInFlight: boolean;
  pendingUtterance: string | null;
  autoHintDone: boolean;
  prefetchedFrame: Promise<string | null> | null;
  problemReadTimer: ReturnType<typeof setTimeout> | undefined;
  problemReadRetried: boolean;
  speechesInProgress: number;
  stop: () => void;
};

const SIGNAL_INTERVAL_MS = 1000;
const MAX_FAILED_SIGNALS = 3;
const GREETING = "見守りを始めるよ";
const FIRST_PROBLEM_READ_MS = 3000;
const NEXT_PROBLEM_READ_MS = 1000;
const PROBLEM_READ_RETRY_MS = 3000;
const MIN_UTTERANCE_CHARS = 3;
const MAX_UTTERANCE_CHARS = 200;
const LISTEN_STATES: State[] = ["watching", "still", "cooldown"];

let activeSession: Session | null = null;

function requireSession(): Session {
  if (!activeSession) throw new Error("セッションが始まっていない。先に startSession を呼ぶ");
  return activeSession;
}

function updateState(session: Session, state: State, problemNo: number): void {
  session.state = state;
  if (problemNo !== session.problemNo) scheduleProblemRead(session, NEXT_PROBLEM_READ_MS);
  session.problemNo = problemNo;
  if (!LISTEN_STATES.includes(state)) {
    stopListening();
    return;
  }
  if (session.running && session.speechesInProgress === 0) startListening((text) => void onHeard(session, text));
}

function say(session: Session, text: string | null): void {
  if (!text) return;
  stopListening();
  session.speechesInProgress += 1;
  speak(text, session.persona)
    .catch((error) => console.warn("[loop] 読み上げに失敗", error))
    .finally(() => {
      session.speechesInProgress -= 1;
      updateState(session, session.state, session.problemNo);
    });
}

function finish(session: Session, problemNo: number): void {
  session.stop();
  stopCamera();
  session.handlers.onState({
    state: "ended",
    still_seconds: 0,
    current_problem_no: problemNo,
    next_action: null,
    cooldown_remaining: 0,
  });
}

function applyResponse(session: Session, speech: string | null, state: State, problemNo: number): void {
  if (!session.running) return;
  say(session, speech);
  if (state === "ended") finish(session, problemNo);
  else updateState(session, state, problemNo);
}

function scheduleProblemRead(session: Session, delayMs: number): void {
  clearTimeout(session.problemReadTimer);
  session.problemReadRetried = false;
  session.problemReadTimer = setTimeout(() => void readCurrentProblem(session), delayMs);
}

async function readCurrentProblem(session: Session): Promise<void> {
  if (!session.running) return;
  const problemNo = session.problemNo;
  try {
    const frameId = await sendFrame(session);
    if (!session.running || problemNo !== session.problemNo) return;
    const response = await readProblem(session.id, session.token, { frame_id: frameId });
    if (session.running && problemNo === session.problemNo && response.problem_no === session.problemNo) {
      session.handlers.onProblem(response.problem_text);
    }
  } catch (error) {
    console.warn("[loop] 問題文の読み取りに失敗", error);
    if (!session.running || problemNo !== session.problemNo || session.problemReadRetried) return;
    session.problemReadRetried = true;
    session.problemReadTimer = setTimeout(() => void readCurrentProblem(session), PROBLEM_READ_RETRY_MS);
  }
}

async function sendFrame(session: Session): Promise<string> {
  const frame = await captureFrame();
  return (await postFrame(session.id, session.token, frame)).frame_id;
}

async function fetchHint(
  session: Session,
  trigger: Trigger,
  prefetchedFrame: Promise<string | null> | null = null,
): Promise<HintResponse> {
  const frameId = (await prefetchedFrame) ?? (await sendFrame(session));
  return requestHint(session.id, session.token, { trigger, frame_id: frameId });
}

function deliverHint(session: Session, hint: HintResponse): void {
  if (!session.running) return;
  session.handlers.onHint(hint);
  applyResponse(session, hint.speech, hint.state, hint.problem_no);
}

async function requestAutoHint(session: Session): Promise<void> {
  session.requestInFlight = true;
  const prefetchedFrame = session.prefetchedFrame;
  session.prefetchedFrame = null;
  try {
    const hint = await fetchHint(session, "auto", prefetchedFrame);
    session.autoHintDone = true;
    deliverHint(session, hint);
  } catch (error) {
    console.warn("[loop] 自動ヒントに失敗。次の秒に再試行", error);
  } finally {
    session.requestInFlight = false;
  }
}

async function onHeard(session: Session, text: string): Promise<void> {
  if (!session.running) return;
  session.handlers.onHeard(text);
  if (text.length < MIN_UTTERANCE_CHARS) return;
  if (session.voiceInFlight) {
    session.pendingUtterance = text;
    return;
  }
  await answerHeard(session, text);
}

async function answerHeard(session: Session, text: string): Promise<void> {
  if (!session.running || !LISTEN_STATES.includes(session.state) || session.requestInFlight) return;
  session.voiceInFlight = true;
  try {
    const frameId = await sendFrame(session);
    const answer = await answerUtterance(session.id, session.token, {
      frame_id: frameId,
      utterance: text.slice(0, MAX_UTTERANCE_CHARS),
    });
    if (answer) deliverHint(session, answer);
  } catch (error) {
    console.warn("[loop] 声への答えに失敗", error);
  } finally {
    session.voiceInFlight = false;
  }
  const next = session.pendingUtterance;
  session.pendingUtterance = null;
  if (next) await answerHeard(session, next);
}

function handleSignal(session: Session, signal: SignalResponse): void {
  session.handlers.onState(signal);
  if (signal.state === "ended") {
    session.stop();
    stopCamera();
    return;
  }
  if (signal.state === "watching" && !session.greeted) {
    session.greeted = true;
    session.problemNo = signal.current_problem_no;
    say(session, GREETING);
    scheduleProblemRead(session, FIRST_PROBLEM_READ_MS);
  }
  updateState(session, signal.state, signal.current_problem_no);
  if (signal.state !== "stuck") session.autoHintDone = false;
  if (signal.state !== "still" && signal.state !== "stuck") session.prefetchedFrame = null;
  if (signal.next_action === "send_frame") {
    session.prefetchedFrame = sendFrame(session).catch((error) => {
      console.warn("[loop] 先読みのフレーム送信に失敗", error);
      return null;
    });
  }
  if (signal.next_action === "send_frame_and_request_hint" && !session.autoHintDone && !session.requestInFlight) {
    void requestAutoHint(session);
  }
}

function setConnection(session: Session, connected: boolean): void {
  if (session.connected === connected) return;
  session.connected = connected;
  session.handlers.onConnection(connected);
}

async function sendSignal(session: Session): Promise<void> {
  if (session.signalInFlight) return;
  session.signalInFlight = true;
  const body: SignalRequest =
    session.latestScore === null
      ? { ts: new Date().toISOString(), camera_ok: session.cameraOk }
      : { ts: new Date().toISOString(), motion: session.latestScore, camera_ok: session.cameraOk };
  try {
    const debugNote = new URLSearchParams(window.location.search).get("debug") === "1" ? voiceStatus() : undefined;
    const signal = await postSignal(session.id, { token: session.token }, body, debugNote);
    if (!session.running) return;
    session.failedSignals = 0;
    setConnection(session, true);
    handleSignal(session, signal);
  } catch (error) {
    if (!session.running) return;
    session.failedSignals += 1;
    if (session.failedSignals >= MAX_FAILED_SIGNALS) setConnection(session, false);
    console.warn("[loop] signals に失敗", error);
  } finally {
    session.signalInFlight = false;
  }
}

export function startSession(
  video: HTMLVideoElement,
  sessionId: string,
  token: string,
  handlers: SessionHandlers,
  persona: Persona = "teacher",
): () => void {
  activeSession?.stop();
  const session: Session = {
    id: sessionId,
    token,
    persona: normalizePersona(persona),
    handlers,
    running: true,
    state: "created",
    problemNo: 1,
    latestScore: null,
    cameraOk: false,
    signalInFlight: false,
    failedSignals: 0,
    connected: null,
    greeted: false,
    requestInFlight: false,
    voiceInFlight: false,
    pendingUtterance: null,
    autoHintDone: false,
    prefetchedFrame: null,
    problemReadTimer: undefined,
    problemReadRetried: false,
    speechesInProgress: 0,
    stop: () => {},
  };

  const stopMotion = startMotionLoop(video, (score, brightness, cameraOk) => {
    session.latestScore = score;
    session.cameraOk = cameraOk;
    if (cameraOk) handlers.onBrightness(brightness);
  });
  const timer = setInterval(() => void sendSignal(session), SIGNAL_INTERVAL_MS);

  session.stop = () => {
    session.running = false;
    clearInterval(timer);
    clearTimeout(session.problemReadTimer);
    stopMotion();
    stopListening();
    if (activeSession === session) activeSession = null;
  };
  activeSession = session;
  return session.stop;
}

// 設定APIの成功後だけ呼ぶ。別セッションの遅い応答は適用しない。
export function updateSessionPersona(sessionId: string, persona: Persona): void {
  if (activeSession?.id === sessionId) activeSession.persona = normalizePersona(persona);
}

export async function requestManualHint(): Promise<HintResponse> {
  const session = requireSession();
  session.requestInFlight = true;
  try {
    const hint = await fetchHint(session, "manual");
    applyResponse(session, hint.speech, hint.state, hint.problem_no);
    return hint;
  } finally {
    session.requestInFlight = false;
  }
}

export async function requestCheck(): Promise<CheckResponse> {
  const session = requireSession();
  session.requestInFlight = true;
  updateState(session, "checking", session.problemNo);
  try {
    const frameId = await sendFrame(session);
    const check = await postCheck(session.id, session.token, { frame_id: frameId });
    applyResponse(session, check.speech, check.state, check.next_problem_no ?? check.problem_no);
    return check;
  } finally {
    session.requestInFlight = false;
  }
}

export async function advance(): Promise<AdvanceResponse> {
  const session = requireSession();
  stopSpeaking();
  const response = await postAdvance(session.id, session.token);
  applyResponse(session, null, response.state, response.current_problem_no);
  return response;
}

export async function end(): Promise<void> {
  const session = requireSession();
  stopSpeaking();
  try {
    await postEnd(session.id, session.token);
  } finally {
    finish(session, session.problemNo);
  }
}
