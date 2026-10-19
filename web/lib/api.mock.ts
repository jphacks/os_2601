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
import type {
  AdvanceResponse,
  Api,
  CheckResponse,
  DemoReset,
  EndResponse,
  HintResponse,
  SessionCreated,
  SessionDetail,
  SessionList,
  Settings,
  SignalResponse,
} from "./api";
import { ApiError } from "./apiError";
import { personaOptions } from "./personas";
import { normalizedSettings } from "./settings";

const SIGNALS_PER_STATE = 5;
const SIGNAL_CYCLE = [
  signalsWatchingMock,
  signalsStillMock,
  signalsStuckMock,
  signalsSpeakingMock,
  signalsCooldownMock,
] as SignalResponse[];
const PROBLEM_COUNT = (sessionActiveMock as SessionDetail).problem_count;
const INITIAL_SETTINGS = normalizedSettings(sessionCreatedMock.settings as Settings);

let signalCount = 0;
let hintCount = 0;
let advanceCount = 0;
let ended = false;
let settings = INITIAL_SETTINGS;

function reset(): void {
  signalCount = 0;
  hintCount = 0;
  advanceCount = 0;
  ended = false;
  settings = INITIAL_SETTINGS;
}

export const mockApi: Api = {
  async createSession(body) {
    reset();
    settings = normalizedSettings({ ...INITIAL_SETTINGS, ...body.settings });
    return { ...sessionCreatedMock, settings } as SessionCreated;
  },

  async openSession() {
    reset();
    return sessionCreatedMock as SessionCreated;
  },

  async listSessions() {
    return sessionsListMock as SessionList;
  },

  async getSession(id) {
    const detail = (id === "ses_mock_ended" ? sessionEndedMock : sessionActiveMock) as SessionDetail;
    return { ...detail, settings, persona_options: personaOptions(detail.persona_options) };
  },

  async patchSettings(_id, _token, body) {
    settings = normalizedSettings({ ...settings, ...body });
    return { settings, state: "created" };
  },

  async postSignal(_id, _auth, body) {
    if (ended) return signalsEndedMock as SignalResponse;
    if (body.force_stuck) return signalsStuckMock as SignalResponse;
    const signal = SIGNAL_CYCLE[Math.floor(signalCount / SIGNALS_PER_STATE) % SIGNAL_CYCLE.length];
    signalCount += 1;
    return signal;
  },

  async postFrame() {
    return frameReceivedMock;
  },

  async requestHint() {
    hintCount += 1;
    return (hintCount === 1 ? hintLevel1Mock : hintLevel2Mock) as HintResponse;
  },

  async answerUtterance() {
    return null;
  },

  async postCheck() {
    return checkCorrectMock as CheckResponse;
  },

  async readProblem() {
    return { problem_no: advanceCount + 1, problem_text: "2x - 7 = 4x + 3", state: "watching" };
  },

  async synthesizeSpeech() {
    throw new ApiError(503, "HINT_UNAVAILABLE", "モックでは VOICEVOX を使わない");
  },

  async postAdvance() {
    advanceCount += 1;
    if (advanceCount >= PROBLEM_COUNT) {
      ended = true;
      return advanceEndedMock as AdvanceResponse;
    }
    return { ...(advanceMock as AdvanceResponse), current_problem_no: advanceCount + 1 };
  },

  async postEnd() {
    ended = true;
    return endMock as EndResponse;
  },

  async demoReset() {
    reset();
    return demoResetMock as DemoReset;
  },
};
