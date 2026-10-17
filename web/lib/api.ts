import advanceMock from "@/mocks/advance.json";
import advanceEndedMock from "@/mocks/advance_ended.json";
import checkCorrectMock from "@/mocks/check_correct.json";
import demoResetMock from "@/mocks/demo_reset.json";
import endMock from "@/mocks/end.json";
import frameReceivedMock from "@/mocks/frame_received.json";
import hintLevel1Mock from "@/mocks/hint_level1.json";
import hintLevel2Mock from "@/mocks/hint_level2.json";
import sessionActiveMock from "@/mocks/session_active.json";
import sessionCreatedMock from "@/mocks/session_created.json";
import sessionEndedMock from "@/mocks/session_ended.json";
import sessionsListMock from "@/mocks/sessions_list.json";
import signalsCooldownMock from "@/mocks/signals_cooldown.json";
import signalsEndedMock from "@/mocks/signals_ended.json";
import signalsSpeakingMock from "@/mocks/signals_speaking.json";
import signalsStillMock from "@/mocks/signals_still.json";
import signalsStuckMock from "@/mocks/signals_stuck.json";
import signalsWatchingMock from "@/mocks/signals_watching.json";
import worksheetWs01Mock from "@/mocks/worksheet_ws01.json";
import worksheetsMock from "@/mocks/worksheets.json";

export type State = "created" | "watching" | "still" | "stuck" | "speaking" | "cooldown" | "checking" | "ended";
export type Mode = "live" | "scripted";
export type Trigger = "auto" | "manual" | "voice";
export type HintSource = "gpt" | "fallback" | "scripted";
export type HintLevel = 1 | 2;
export type Verdict = "correct" | "incorrect" | "unreadable";
export type ProblemStatus = "pending" | "working" | "done" | "skipped";

export type LeakCheck = { ok: boolean; fallback: boolean };

export type Settings = { stuck_seconds: number; cooldown_seconds: number; max_level: number };

export type SessionCreateRequest = {
  worksheet_id: string;
  learner_label?: string;
  mode: Mode;
  settings?: Partial<Settings>;
};

export type SessionCreated = {
  session_id: string;
  session_token: string;
  mode: Mode;
  state: State;
  worksheet: { worksheet_id: string; title: string; problem_count: number };
  settings: Settings;
  created_at: string;
};

export type SessionList = {
  sessions: {
    session_id: string;
    worksheet_id: string;
    learner_label: string;
    mode: Mode;
    state: State;
    problem_done: number;
    problem_count: number;
    stuck_total: number;
    created_at: string;
    ended_at: string | null;
  }[];
};

export type SessionDetail = {
  session_id: string;
  worksheet_id: string;
  worksheet_title: string;
  problem_count: number;
  learner_label: string;
  mode: Mode;
  state: State;
  current_problem_no: number;
  still_seconds: number;
  settings: Settings;
  problems: {
    problem_no: number;
    status: ProblemStatus;
    stuck_count: number;
    max_level: number;
    seconds_spent: number;
    hints: {
      hint_id: string;
      level: HintLevel;
      trigger: Trigger;
      display: string;
      stuck_point: string;
      source: HintSource;
      leak_check: LeakCheck;
      latency_ms: number;
      created_at: string;
    }[];
    check: { verdict: Verdict; display: string; created_at: string } | null;
  }[];
  stuck_points: { label: string; count: number }[];
  leak_blocked_count: number;
  created_at: string;
  ended_at: string | null;
};

export type SettingsPatch = Partial<Pick<Settings, "stuck_seconds" | "cooldown_seconds">>;

export type SignalRequest =
  | { ts: string; motion?: number; camera_ok: boolean; force_stuck?: false }
  | { ts: string; motion?: number; camera_ok?: boolean; force_stuck: true };

export type SignalResponse = {
  state: State;
  still_seconds: number;
  current_problem_no: number;
  next_action: "send_frame_and_request_hint" | "send_frame" | null;
  cooldown_remaining: number;
};

export type FrameReceived = { frame_id: string; received_at: string; bytes: number };

export type HintRequest = { trigger: Trigger; frame_id: string };

export type HintResponse = {
  hint_id: string;
  problem_no: number;
  level: HintLevel;
  trigger: Trigger;
  speech: string | null;
  display: string;
  stuck_point: string;
  leak_check: LeakCheck;
  source: HintSource;
  model?: string;
  latency_ms: number;
  state: State;
};

export type CheckRequest = { frame_id: string };

export type CheckResponse = {
  check_id: string;
  problem_no: number;
  verdict: Verdict;
  speech: string;
  display: string;
  next_problem_no: number | null;
  state: State;
};

export type AdvanceResponse = { current_problem_no: number; state: State };

export type EndResponse = { state: "ended"; ended_at: string };

export type WorksheetList = {
  worksheets: { worksheet_id: string; title: string; problem_count: number; grade: string }[];
};

export type WorksheetDetail = {
  worksheet_id: string;
  title: string;
  grade: string;
  problems: { problem_no: number; text: string }[];
  print: { paper: string; id_font_px: number; gap_mm: number; footer: string };
};

export type DemoReset = { ok: true; removed_sessions: number };

export type Health = { ok: boolean; gpt: "ok" | "missing"; worksheets: number; mode_default: Mode };

export type ErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "STATE_CONFLICT"
  | "FRAME_TOO_LARGE"
  | "VALIDATION_ERROR"
  | "HINT_UNAVAILABLE";

export type ApiErrorBody = { error: { code: ErrorCode; message: string } };

export type Auth = { token: string } | { operatorKey: string };

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ErrorCode | "UNKNOWN",
    detail = "",
  ) {
    super(detail ? `API ${status} ${code}: ${detail}` : `API ${status} ${code}`);
    this.name = "ApiError";
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const USE_MOCK = process.env.NEXT_PUBLIC_MOCK === "1";

const SIGNAL_TIMEOUT_MS = 3000;
const FRAME_TIMEOUT_MS = 5000;
const SIGNALS_PER_STATE = 5;
const SIGNAL_CYCLE = [
  signalsWatchingMock,
  signalsStillMock,
  signalsStuckMock,
  signalsSpeakingMock,
  signalsCooldownMock,
] as SignalResponse[];
const MOCK_PROBLEM_COUNT = (sessionActiveMock as SessionDetail).problem_count;

let mockSignalCount = 0;
let mockHintCount = 0;
let mockAdvanceCount = 0;
let mockEnded = false;

function resetMockState(): void {
  mockSignalCount = 0;
  mockHintCount = 0;
  mockAdvanceCount = 0;
  mockEnded = false;
}

function sessionPath(id: string, action = ""): string {
  return `/sessions/${encodeURIComponent(id)}${action}`;
}

function authHeaders(auth: Auth): Record<string, string> {
  return "token" in auth ? { Authorization: `Bearer ${auth.token}` } : { "X-Operator-Key": auth.operatorKey };
}

function jsonInit(method: string, auth: Auth, body?: unknown): RequestInit {
  return {
    method,
    headers: { ...authHeaders(auth), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_BASE が無い。web/.env.local か Vercel の環境変数に入れる");
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const body: ApiErrorBody | null = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.code ?? "UNKNOWN", body?.error?.message);
  }
  return response.json() as Promise<T>;
}

export async function createSession(body: SessionCreateRequest, operatorKey: string): Promise<SessionCreated> {
  if (USE_MOCK) {
    resetMockState();
    return sessionCreatedMock as SessionCreated;
  }
  return request("/sessions", jsonInit("POST", { operatorKey }, body));
}

export async function listSessions(operatorKey: string): Promise<SessionList> {
  if (USE_MOCK) return sessionsListMock as SessionList;
  return request("/sessions", { headers: authHeaders({ operatorKey }) });
}

export async function getSession(id: string, auth: Auth): Promise<SessionDetail> {
  if (USE_MOCK) return (id === "ses_mock_ended" ? sessionEndedMock : sessionActiveMock) as SessionDetail;
  return request(sessionPath(id), { headers: authHeaders(auth) });
}

export async function patchSettings(
  id: string,
  token: string,
  body: SettingsPatch,
): Promise<{ settings: Settings; state: State }> {
  if (USE_MOCK) return { settings: { ...(sessionCreatedMock as SessionCreated).settings, ...body }, state: "created" };
  return request(sessionPath(id, "/settings"), jsonInit("PATCH", { token }, body));
}

export async function postSignal(id: string, auth: Auth, body: SignalRequest): Promise<SignalResponse> {
  if (USE_MOCK) {
    if (mockEnded) return signalsEndedMock as SignalResponse;
    if (body.force_stuck) return signalsStuckMock as SignalResponse;
    const signal = SIGNAL_CYCLE[Math.floor(mockSignalCount / SIGNALS_PER_STATE) % SIGNAL_CYCLE.length];
    mockSignalCount += 1;
    return signal;
  }
  const timeout = new AbortController();
  setTimeout(() => timeout.abort(), SIGNAL_TIMEOUT_MS);
  return request(sessionPath(id, "/signals"), { ...jsonInit("POST", auth, body), signal: timeout.signal });
}

export async function postFrame(id: string, token: string, blob: Blob): Promise<FrameReceived> {
  if (USE_MOCK) return frameReceivedMock;
  const form = new FormData();
  form.append("frame", blob, "frame.jpg");
  const timeout = new AbortController();
  setTimeout(() => timeout.abort(), FRAME_TIMEOUT_MS);
  return request(sessionPath(id, "/frames"), {
    method: "POST",
    headers: authHeaders({ token }),
    body: form,
    signal: timeout.signal,
  });
}

export async function requestHint(id: string, token: string, body: HintRequest): Promise<HintResponse> {
  if (USE_MOCK) {
    mockHintCount += 1;
    return (mockHintCount === 1 ? hintLevel1Mock : hintLevel2Mock) as HintResponse;
  }
  return request(sessionPath(id, "/hints"), jsonInit("POST", { token }, body));
}

export async function postCheck(id: string, token: string, body: CheckRequest): Promise<CheckResponse> {
  if (USE_MOCK) return checkCorrectMock as CheckResponse;
  return request(sessionPath(id, "/check"), jsonInit("POST", { token }, body));
}

export async function postAdvance(id: string, token: string): Promise<AdvanceResponse> {
  if (USE_MOCK) {
    mockAdvanceCount += 1;
    if (mockAdvanceCount >= MOCK_PROBLEM_COUNT) {
      mockEnded = true;
      return advanceEndedMock as AdvanceResponse;
    }
    return { ...(advanceMock as AdvanceResponse), current_problem_no: mockAdvanceCount + 1 };
  }
  return request(sessionPath(id, "/advance"), jsonInit("POST", { token }, { reason: "skip" }));
}

export async function postEnd(id: string, token: string): Promise<EndResponse> {
  if (USE_MOCK) {
    mockEnded = true;
    return endMock as EndResponse;
  }
  return request(sessionPath(id, "/end"), { method: "POST", headers: authHeaders({ token }) });
}

export async function getWorksheets(): Promise<WorksheetList> {
  if (USE_MOCK) return worksheetsMock;
  return request("/worksheets");
}

export async function getWorksheet(id: string): Promise<WorksheetDetail> {
  if (USE_MOCK) return worksheetWs01Mock;
  return request(`/worksheets/${encodeURIComponent(id)}`);
}

export async function demoReset(operatorKey: string): Promise<DemoReset> {
  if (USE_MOCK) {
    resetMockState();
    return demoResetMock as DemoReset;
  }
  return request("/demo/reset", { method: "POST", headers: authHeaders({ operatorKey }) });
}
