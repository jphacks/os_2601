import advanceMock from "@/mocks/advance.json";
import checkCorrectMock from "@/mocks/check_correct.json";
import hintLevel1Mock from "@/mocks/hint_level1.json";
import hintLevel2Mock from "@/mocks/hint_level2.json";
import signalsCooldownMock from "@/mocks/signals_cooldown.json";
import signalsSpeakingMock from "@/mocks/signals_speaking.json";
import signalsStillMock from "@/mocks/signals_still.json";
import signalsStuckMock from "@/mocks/signals_stuck.json";
import signalsWatchingMock from "@/mocks/signals_watching.json";

import type { AdvanceResponse, CheckResponse, HintResponse, SignalResponse } from "./api";
import { speak } from "./speech";

export type SessionHandlers = {
  onState: (signal: SignalResponse) => void;
  onHint: (hint: HintResponse) => void;
  onBrightness: (brightness: number) => void;
  onConnection: (connected: boolean) => void;
  onHeard: (text: string) => void;
};

const STATE_INTERVAL_MS = 5000;
const STUB_BRIGHTNESS = 120;
const STATE_CYCLE = [
  signalsWatchingMock,
  signalsStillMock,
  signalsStuckMock,
  signalsSpeakingMock,
  signalsCooldownMock,
] as SignalResponse[];

export function startSession(
  video: HTMLVideoElement,
  sessionId: string,
  token: string,
  handlers: SessionHandlers,
): () => void {
  let step = 0;
  const emitNextState = () => {
    const signal = STATE_CYCLE[step % STATE_CYCLE.length];
    step += 1;
    handlers.onState(signal);
    handlers.onBrightness(STUB_BRIGHTNESS);
    if (signal.state !== "stuck") return;
    const hint = hintLevel1Mock as HintResponse;
    handlers.onHint(hint);
    if (hint.speech) void speak(hint.speech);
  };

  handlers.onConnection(true);
  emitNextState();
  const timer = setInterval(emitNextState, STATE_INTERVAL_MS);
  return () => clearInterval(timer);
}

export async function requestManualHint(): Promise<HintResponse> {
  return hintLevel2Mock as HintResponse;
}

export async function requestCheck(): Promise<CheckResponse> {
  return checkCorrectMock as CheckResponse;
}

export async function advance(): Promise<AdvanceResponse> {
  return advanceMock as AdvanceResponse;
}

export async function end(): Promise<void> {
  console.log("[loop] end（空実装。本物は T1-2）");
}
