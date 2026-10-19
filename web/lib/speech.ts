import { synthesizeSpeech, type VoiceCharacter } from "./api";
import { SILENT_WAV } from "./silentWav";

const LANG = "ja-JP";
const VOICES_WAIT_MS = 1000;
const PLAYBACK_LIMIT_MS = 30000;
const CANCELLED_ERRORS = new Set(["interrupted", "canceled"]);

type SpeechSession = { id: string; token: string };

let japaneseVoiceLookup: Promise<SpeechSynthesisVoice | undefined> | null = null;
let speaker: SpeechSession | null = null;
let character: VoiceCharacter = "handsome";
let player: HTMLAudioElement | null = null;
let speechTurn = 0;
let abandonSynthesis: (() => void) | null = null;

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

async function speakWithVoicevox(
  text: string,
  turn: number,
  session: SpeechSession,
  audioPlayer: HTMLAudioElement,
): Promise<void> {
  const audio = await Promise.race([
    synthesizeSpeech(session.id, session.token, text, character),
    new Promise<null>((resolve) => {
      abandonSynthesis = () => resolve(null);
    }),
  ]);
  if (turn !== speechTurn || !audio) return;
  await playAudio(audioPlayer, audio);
}

async function speakWithBrowserVoice(text: string, turn: number): Promise<void> {
  if (!isSupported()) throw new Error("このブラウザは読み上げに対応していない");
  const voice = await loadJapaneseVoice();
  if (turn !== speechTurn) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = LANG;
  utterance.rate = 1;
  utterance.pitch = 1;
  if (voice) utterance.voice = voice;
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

export async function speak(text: string): Promise<void> {
  stopSpeaking();
  const turn = speechTurn;
  if (speaker && player) {
    try {
      await speakWithVoicevox(text, turn, speaker, player);
      return;
    } catch (error) {
      if (turn !== speechTurn) return;
      console.warn("[speech] VOICEVOX の声が使えないので、ブラウザの声で読む", error);
    }
  }
  await speakWithBrowserVoice(text, turn);
}
