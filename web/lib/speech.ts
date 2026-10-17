const LANG = "ja-JP";
const VOICES_WAIT_MS = 1000;
const CANCELLED_ERRORS = new Set(["interrupted", "canceled"]);

let japaneseVoiceLookup: Promise<SpeechSynthesisVoice | undefined> | null = null;

function isSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

function waitForVoices(): Promise<void> {
  if (speechSynthesis.getVoices().length > 0) return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      speechSynthesis.removeEventListener("voiceschanged", done);
      resolve();
    };
    const timer = setTimeout(done, VOICES_WAIT_MS);
    speechSynthesis.addEventListener("voiceschanged", done);
  });
}

function loadJapaneseVoice(): Promise<SpeechSynthesisVoice | undefined> {
  japaneseVoiceLookup ??= waitForVoices().then(() =>
    speechSynthesis.getVoices().find((voice) => voice.lang.replace("_", "-") === LANG),
  );
  return japaneseVoiceLookup;
}

export function unlockSpeech(): void {
  if (!isSupported()) return;
  speechSynthesis.speak(new SpeechSynthesisUtterance(""));
}

export function stopSpeaking(): void {
  if (isSupported()) speechSynthesis.cancel();
}

export async function speak(text: string): Promise<void> {
  if (!isSupported()) throw new Error("このブラウザは読み上げに対応していない");
  const voice = await loadJapaneseVoice();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = LANG;
  utterance.rate = 1;
  utterance.pitch = 1;
  if (voice) utterance.voice = voice;
  stopSpeaking();
  await new Promise<void>((resolve, reject) => {
    utterance.onend = () => resolve();
    utterance.onerror = (event) =>
      CANCELLED_ERRORS.has(event.error) ? resolve() : reject(new Error(`読み上げに失敗した: ${event.error}`));
    speechSynthesis.speak(utterance);
  });
}
