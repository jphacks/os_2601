import {
  postAdvance,
  postCheck,
  postEnd,
  postFrame,
  postSignal,
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
import { speak, stopSpeaking } from "./speech";
import { startListening, stopListening } from "./voice";

export type SessionHandlers = {
  onState: (signal: SignalResponse) => void;
  onHint: (hint: HintResponse) => void;
  onBrightness: (brightness: number) => void;
  onConnection: (connected: boolean) => void;
  onHeard: (text: string) => void;
};

type Session = {
  id: string;
  token: string;
  handlers: SessionHandlers;
  state: State;
  problemNo: number;
  latestScore: number | null;
  cameraOk: boolean;
  signalInFlight: boolean;
  failedSignals: number;
  connected: boolean | null;
  greeted: boolean;
  autoHintInFlight: boolean;
  autoHintDone: boolean;
  voiceHintInFlight: boolean;
  listening: boolean;
  stop: () => void;
};

const SIGNAL_INTERVAL_MS = 1000;
const MAX_FAILED_SIGNALS = 3;
const GREETING = "見守りを始めるよ";
const VOICE_KEYWORDS = ["わからない", "わかんない", "ヒント"];
const HINTABLE_STATES: State[] = ["watching", "still", "cooldown"];
const LISTEN_STATES: State[] = ["watching", "cooldown"];
const MUTE_STATES: State[] = ["speaking", "checking"];

let activeSession: Session | null = null;

function say(text: string | null): void {
  if (!text) return;
  speak(text).catch((error) => console.warn("[loop] 読み上げに失敗", error));
}

function requireSession(): Session {
  if (!activeSession) throw new Error("セッションが始まっていない。先に startSession を呼ぶ");
  return activeSession;
}

function endedSignal(problemNo: number): SignalResponse {
  return { state: "ended", still_seconds: 0, current_problem_no: problemNo, next_action: null, cooldown_remaining: 0 };
}

function finish(session: Session, problemNo: number): void {
  session.stop();
  session.handlers.onState(endedSignal(problemNo));
}

function setConnection(session: Session, connected: boolean): void {
  if (session.connected === connected) return;
  session.connected = connected;
  session.handlers.onConnection(connected);
}

function updateState(session: Session, state: State, problemNo: number): void {
  session.state = state;
  session.problemNo = problemNo;
  if (MUTE_STATES.includes(state) && session.listening) {
    stopListening();
    session.listening = false;
  }
  if (LISTEN_STATES.includes(state) && !session.listening) {
    startListening((text) => void onHeard(session, text));
    session.listening = true;
  }
}

async function sendFrame(session: Session): Promise<string> {
  const frame = await captureFrame();
  return (await postFrame(session.id, session.token, frame)).frame_id;
}

async function fetchHint(session: Session, trigger: Trigger): Promise<HintResponse> {
  const frameId = await sendFrame(session);
  return requestHint(session.id, session.token, { trigger, frame_id: frameId });
}

function deliverHint(session: Session, hint: HintResponse): void {
  session.handlers.onHint(hint);
  say(hint.speech);
  if (hint.state === "ended") finish(session, hint.problem_no);
}

async function requestAutoHint(session: Session): Promise<void> {
  session.autoHintInFlight = true;
  try {
    const hint = await fetchHint(session, "auto");
    session.autoHintDone = true;
    deliverHint(session, hint);
  } catch (error) {
    console.warn("[loop] 自動ヒントに失敗。次の秒に再試行", error);
  } finally {
    session.autoHintInFlight = false;
  }
}

async function onHeard(session: Session, text: string): Promise<void> {
  session.handlers.onHeard(text);
  if (!VOICE_KEYWORDS.some((keyword) => text.includes(keyword))) return;
  if (!HINTABLE_STATES.includes(session.state) || session.voiceHintInFlight) return;
  session.voiceHintInFlight = true;
  try {
    deliverHint(session, await fetchHint(session, "voice"));
  } catch (error) {
    console.warn("[loop] 声のヒントに失敗", error);
  } finally {
    session.voiceHintInFlight = false;
  }
}

function handleSignal(session: Session, signal: SignalResponse): void {
  session.handlers.onState(signal);
  updateState(session, signal.state, signal.current_problem_no);
  if (signal.state === "ended") {
    session.stop();
    return;
  }
  if (signal.state === "watching" && !session.greeted) {
    session.greeted = true;
    say(GREETING);
  }
  if (signal.state !== "stuck") session.autoHintDone = false;
  if (signal.next_action === "send_frame_and_request_hint" && !session.autoHintDone && !session.autoHintInFlight) {
    void requestAutoHint(session);
  }
}

async function sendSignal(session: Session): Promise<void> {
  if (session.signalInFlight) return;
  session.signalInFlight = true;
  const body: SignalRequest =
    session.latestScore === null
      ? { ts: new Date().toISOString(), camera_ok: session.cameraOk }
      : { ts: new Date().toISOString(), motion: session.latestScore, camera_ok: session.cameraOk };
  try {
    const signal = await postSignal(session.id, { token: session.token }, body);
    session.failedSignals = 0;
    setConnection(session, true);
    handleSignal(session, signal);
  } catch (error) {
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
): () => void {
  activeSession?.stop();
  const session: Session = {
    id: sessionId,
    token,
    handlers,
    state: "created",
    problemNo: 1,
    latestScore: null,
    cameraOk: false,
    signalInFlight: false,
    failedSignals: 0,
    connected: null,
    greeted: false,
    autoHintInFlight: false,
    autoHintDone: false,
    voiceHintInFlight: false,
    listening: false,
    stop: () => {},
  };

  const stopMotion = startMotionLoop(video, (score, brightness, cameraOk) => {
    session.latestScore = score;
    session.cameraOk = cameraOk;
    if (cameraOk) handlers.onBrightness(brightness);
  });
  const timer = setInterval(() => void sendSignal(session), SIGNAL_INTERVAL_MS);

  session.stop = () => {
    clearInterval(timer);
    stopMotion();
    if (session.listening) stopListening();
    session.listening = false;
    if (activeSession === session) activeSession = null;
  };
  activeSession = session;
  return session.stop;
}

export async function requestManualHint(): Promise<HintResponse> {
  const session = requireSession();
  const hint = await fetchHint(session, "manual");
  say(hint.speech);
  if (hint.state === "ended") finish(session, hint.problem_no);
  return hint;
}

export async function requestCheck(): Promise<CheckResponse> {
  const session = requireSession();
  const frameId = await sendFrame(session);
  const check = await postCheck(session.id, session.token, { frame_id: frameId });
  say(check.speech);
  if (check.state === "ended") finish(session, check.problem_no);
  return check;
}

export async function advance(): Promise<AdvanceResponse> {
  const session = requireSession();
  stopSpeaking();
  const response = await postAdvance(session.id, session.token);
  if (response.state === "ended") finish(session, response.current_problem_no);
  return response;
}

export async function end(): Promise<void> {
  const session = requireSession();
  await postEnd(session.id, session.token);
  finish(session, session.problemNo);
  stopCamera();
}
