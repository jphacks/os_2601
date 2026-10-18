import { synthesizeSpeech, type VoiceCharacter } from "./api";

const LANG = "ja-JP";
const VOICES_WAIT_MS = 1000;
const CANCELLED_ERRORS = new Set(["interrupted", "canceled"]);
const SILENT_WAV = "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==";

let japaneseVoiceLookup: Promise<SpeechSynthesisVoice | undefined> | null = null;
let speaker: { id: string; token: string } | null = null;
let character: VoiceCharacter = "handsome";
let player: HTMLAudioElement | null = null;
let speechTurn = 0;
let abandonSynthesis: (() => void) | null = null;
let speaking: Promise<void> = Promise.resolve();
const PLAYBACK_LIMIT_MS = 30000;

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

export function setSpeechSession(id: string, token: string): void {
  speaker = { id, token };
}

export function setSpeechCharacter(next: VoiceCharacter): void {
  character = next;
}

export function unlockSpeech(): void {
  if (typeof window === "undefined") return;
  player ??= new Audio();
  player.src = SILENT_WAV;
  player.play().catch((error) => console.warn("[speech] 無音の再生に失敗", error));
  if (isSupported()) speechSynthesis.speak(new SpeechSynthesisUtterance(""));
}

export function stopSpeaking(): void {
  speechTurn += 1;
  abandonSynthesis?.();
  abandonSynthesis = null;
  player?.pause();
  if (isSupported()) speechSynthesis.cancel();
}

function playAudio(audioPlayer: HTMLAudioElement, audio: Blob): Promise<void> {
  const url = URL.createObjectURL(audio);
  audioPlayer.src = url;
  let limit: ReturnType<typeof setTimeout> | undefined;
  return new Promise<void>((resolve, reject) => {
    audioPlayer.onpause = () => resolve();
    audioPlayer.onended = () => resolve();
    audioPlayer.onerror = () => reject(new Error("音声を再生できなかった"));
    limit = setTimeout(() => {
      audioPlayer.pause();
      resolve();
    }, PLAYBACK_LIMIT_MS);
    audioPlayer.play().catch(reject);
  }).finally(() => {
    clearTimeout(limit);
    URL.revokeObjectURL(url);
  });
}

export function speak(text: string): Promise<void> {
  const spoken = speakNow(text);
  speaking = spoken.catch(() => undefined);
  return spoken;
}

// 今の読み上げ（「できた」の判定など）を言い終えてから読む。間に止められたら読まない
export async function speakNext(text: string): Promise<void> {
  const turn = speechTurn;
  await speaking;
  if (turn === speechTurn) await speak(text);
}

async function speakNow(text: string): Promise<void> {
  stopSpeaking();
  const turn = speechTurn;
  if (speaker && player) {
    try {
      const audio = await Promise.race([
        synthesizeSpeech(speaker.id, speaker.token, text, character),
        new Promise<null>((resolve) => {
          abandonSynthesis = () => resolve(null);
        }),
      ]);
      if (turn !== speechTurn || !audio) return;
      await playAudio(player, audio);
      return;
    } catch (error) {
      if (turn !== speechTurn) return;
      console.warn("[speech] VOICEVOX の声が使えないので、ブラウザの声で読む", error);
    }
  }
  if (!isSupported()) throw new Error("このブラウザは読み上げに対応していない");
  const voice = await loadJapaneseVoice();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = LANG;
  utterance.rate = 1;
  utterance.pitch = 1;
  if (voice) utterance.voice = voice;
  if (turn !== speechTurn) return;
  let limit: ReturnType<typeof setTimeout> | undefined;
  await new Promise<void>((resolve, reject) => {
    utterance.onend = () => resolve();
    utterance.onerror = (event) =>
      CANCELLED_ERRORS.has(event.error) ? resolve() : reject(new Error(`読み上げに失敗した: ${event.error}`));
    limit = setTimeout(() => {
      speechSynthesis.cancel();
      resolve();
    }, PLAYBACK_LIMIT_MS);
    speechSynthesis.speak(utterance);
  }).finally(() => clearTimeout(limit));
}
