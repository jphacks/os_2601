import { mockApi } from "./api.mock";
import { ApiError } from "./apiError";
import { personaOptions, type Persona, type PersonaOption, type VoiceCharacter } from "./personas";

export { ApiError, type ApiErrorBody, type ErrorCode } from "./apiError";
export type { Persona, PersonaOption, VoiceCharacter } from "./personas";

export type State = "created" | "watching" | "still" | "stuck" | "speaking" | "cooldown" | "checking" | "ended";
export type Mode = "live" | "scripted";
export type Trigger = "auto" | "manual" | "voice";
export type HintSource = "ai" | "fallback" | "scripted";
export type HintLevel = 1 | 2;
export type Verdict = "correct" | "incorrect" | "unreadable";
export type ProblemStatus = "pending" | "working" | "done" | "skipped";

export type LeakCheck = { ok: boolean; fallback: boolean };

export type Settings = { stuck_seconds: number; cooldown_seconds: number; max_level: number; persona: Persona };

export type SessionCreateRequest = {
  worksheet_id: "FREE";
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
  persona_options: PersonaOption[];
  problems: {
    problem_no: number;
    problem_text: string | null;
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

export type SettingsPatch = Partial<Pick<Settings, "stuck_seconds" | "cooldown_seconds" | "persona">>;

export type SettingsResponse = { settings: Settings; state: State };

export type SignalRequest =
  | { motion?: number; camera_ok: boolean; force_stuck?: false }
  | { motion?: number; camera_ok?: boolean; force_stuck: true };

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
  problem_text: string | null;
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

export type ProblemResponse = { problem_no: number; problem_text: string | null; state: State };

export type AdvanceResponse = { current_problem_no: number; state: State };

export type EndResponse = { state: "ended"; ended_at: string };

export type DemoReset = { ok: true; removed_sessions: number };

export type Auth = { token: string } | { operatorKey: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const USE_MOCK = process.env.NEXT_PUBLIC_MOCK === "1";

const REQUEST_TIMEOUT_MS = 15000;
const SIGNAL_TIMEOUT_MS = 3000;
const FRAME_TIMEOUT_MS = 5000;
const SPEECH_TIMEOUT_MS = 9000;

function normalizedSettings(settings: Settings): Settings {
  return { ...settings, persona: settings.persona ?? "teacher" };
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

async function send(path: string, init: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_BASE が無い。web/.env.local か Vercel の環境変数に入れる");
  const response = await fetch(`${API_BASE}${path}`, { ...init, signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) throw await ApiError.fromResponse(response);
  return response;
}

async function request<T>(path: string, init: RequestInit, timeoutMs?: number): Promise<T> {
  return (await send(path, init, timeoutMs)).json() as Promise<T>;
}

const httpApi = {
  async createSession(body: SessionCreateRequest, operatorKey: string): Promise<SessionCreated> {
    return request("/sessions", jsonInit("POST", { operatorKey }, body));
  },

  async openSession(): Promise<SessionCreated> {
    return request("/sessions/open", { method: "POST" });
  },

  async listSessions(operatorKey: string): Promise<SessionList> {
    return request("/sessions", { headers: authHeaders({ operatorKey }) });
  },

  async getSession(id: string, auth: Auth): Promise<SessionDetail> {
    const detail = await request<SessionDetail>(sessionPath(id), { headers: authHeaders(auth) });
    return {
      ...detail,
      settings: normalizedSettings(detail.settings),
      persona_options: personaOptions(detail.persona_options),
    };
  },

  async patchSettings(id: string, token: string, body: SettingsPatch): Promise<SettingsResponse> {
    const response = await request<SettingsResponse>(sessionPath(id, "/settings"), jsonInit("PATCH", { token }, body));
    return { ...response, settings: normalizedSettings(response.settings) };
  },

  async postSignal(id: string, auth: Auth, body: SignalRequest, debugNote?: string): Promise<SignalResponse> {
    const query = debugNote ? `?note=${encodeURIComponent(debugNote)}` : "";
    return request(sessionPath(id, `/signals${query}`), jsonInit("POST", auth, body), SIGNAL_TIMEOUT_MS);
  },

  async postFrame(id: string, token: string, blob: Blob): Promise<FrameReceived> {
    const form = new FormData();
    form.append("frame", blob, "frame.jpg");
    return request(
      sessionPath(id, "/frames"),
      { method: "POST", headers: authHeaders({ token }), body: form },
      FRAME_TIMEOUT_MS,
    );
  },

  async requestHint(id: string, token: string, body: HintRequest): Promise<HintResponse> {
    return request(sessionPath(id, "/hints"), jsonInit("POST", { token }, body));
  },

  async answerUtterance(
    id: string,
    token: string,
    body: { frame_id: string; utterance: string },
  ): Promise<HintResponse | null> {
    const response = await send(sessionPath(id, "/hints"), jsonInit("POST", { token }, { trigger: "voice", ...body }));
    return response.status === 204 ? null : (response.json() as Promise<HintResponse>);
  },

  async postCheck(id: string, token: string, body: CheckRequest): Promise<CheckResponse> {
    return request(sessionPath(id, "/check"), jsonInit("POST", { token }, body));
  },

  async readProblem(id: string, token: string, body: { frame_id: string }): Promise<ProblemResponse> {
    return request(sessionPath(id, "/problem"), jsonInit("POST", { token }, body));
  },

  async synthesizeSpeech(id: string, token: string, text: string, character: VoiceCharacter): Promise<Blob> {
    const response = await send(sessionPath(id, "/tts"), jsonInit("POST", { token }, { text, character }), SPEECH_TIMEOUT_MS);
    return response.blob();
  },

  async postAdvance(id: string, token: string): Promise<AdvanceResponse> {
    return request(sessionPath(id, "/advance"), jsonInit("POST", { token }));
  },

  async postEnd(id: string, token: string): Promise<EndResponse> {
    return request(sessionPath(id, "/end"), { method: "POST", headers: authHeaders({ token }) });
  },

  async demoReset(operatorKey: string): Promise<DemoReset> {
    return request("/demo/reset", { method: "POST", headers: authHeaders({ operatorKey }) });
  },
};

export type Api = typeof httpApi;

export const {
  createSession,
  openSession,
  listSessions,
  getSession,
  patchSettings,
  postSignal,
  postFrame,
  requestHint,
  answerUtterance,
  postCheck,
  readProblem,
  synthesizeSpeech,
  postAdvance,
  postEnd,
  demoReset,
} = USE_MOCK ? mockApi : httpApi;

