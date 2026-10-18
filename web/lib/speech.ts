import { normalizePersona, type Persona } from "./personas";
import { selectJapaneseVoice, SPEECH_PROFILES } from "./speech-profile";

const VOICES_WAIT_MS = 1000;
const SPEECH_TIMEOUT_MS = 15000;
let speechVersion = 0;
let finishCurrent: (() => void) | null = null;

function synthesis(): SpeechSynthesis | null {
  try {
    return typeof window !== "undefined" && typeof SpeechSynthesisUtterance === "function"
      ? window.speechSynthesis ?? null
      : null;
  } catch {
    return null;
  }
}

function waitForVoices(engine: SpeechSynthesis): Promise<void> {
  try {
    if (engine.getVoices().length > 0) return Promise.resolve();
  } catch {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      try {
        engine.removeEventListener?.("voiceschanged", done);
      } catch {
        // イベント解除に非対応でも待機は終了する。
      }
      resolve();
    };
    const timer = setTimeout(done, VOICES_WAIT_MS);
    try {
      engine.addEventListener?.("voiceschanged", done);
    } catch {
      done();
    }
  });
}

export function unlockSpeech(): void {
  try {
    synthesis()?.speak(new SpeechSynthesisUtterance(""));
  } catch {
    // 音声が使えない場合も、カメラ開始や字幕表示は続ける。
  }
}

export function stopSpeaking(): void {
  speechVersion += 1;
  finishCurrent?.();
  finishCurrent = null;
  try {
    synthesis()?.cancel();
  } catch {
    // 一部のブラウザの実装エラーで終了処理を止めない。
  }
}

export async function speak(text: string, persona: Persona = "teacher"): Promise<void> {
  const version = ++speechVersion;
  finishCurrent?.();
  finishCurrent = null;
  const engine = synthesis();
  if (!engine || !text) return;
  await waitForVoices(engine);
  if (version !== speechVersion) return;
  try {
    const profile = SPEECH_PROFILES[normalizePersona(persona)];
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = profile.language;
    let voice: SpeechSynthesisVoice | undefined;
    try {
      voice = selectJapaneseVoice(engine.getVoices(), profile);
      if (voice) utterance.voice = voice;
    } catch {
      voice = undefined;
      // 音声選択に対応していなければ、ブラウザ標準の日本語読み上げを使う。
    }
    try {
      // 日本語の候補がない環境では、既存の標準値を使う。
      utterance.rate = voice ? profile.rate : 1;
      utterance.pitch = voice ? profile.pitch : 1;
    } catch {
      try {
        utterance.rate = 1;
        utterance.pitch = 1;
      } catch {
        // rate/pitch自体が非対応なら既定値のまま読む。
      }
    }
    try {
      engine.cancel();
    } catch {
      // cancel非対応でも新しい字幕・発話は処理する。
    }
    await new Promise<void>((resolve) => {
      const done = () => {
        clearTimeout(timer);
        if (finishCurrent === done) finishCurrent = null;
        resolve();
      };
      const timer = setTimeout(done, SPEECH_TIMEOUT_MS);
      finishCurrent = done;
      utterance.onend = done;
      utterance.onerror = done;
      try {
        engine.speak(utterance);
      } catch {
        done();
      }
    });
  } catch {
    // 字幕が主情報。音声APIやコンストラクターの失敗はアプリを落とさない。
  }
}
