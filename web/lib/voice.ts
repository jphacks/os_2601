const LANG = "ja-JP";
const RESTART_DELAY_MS = 500;
const PERMISSION_ERRORS = new Set(["not-allowed", "service-not-allowed"]);

type RecognitionResultEvent = { resultIndex: number; results: SpeechRecognitionResultList };

type Recognizer = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  abort: () => void;
};

type RecognizerClass = new () => Recognizer;

let active: Recognizer | null = null;
let restartTimer: ReturnType<typeof setTimeout> | undefined;

function findRecognizerClass(): RecognizerClass | undefined {
  if (typeof window === "undefined") return undefined;
  const speechWindow = window as unknown as {
    SpeechRecognition?: RecognizerClass;
    webkitSpeechRecognition?: RecognizerClass;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

function begin(recognizer: Recognizer): void {
  try {
    recognizer.start();
  } catch (error) {
    console.warn("[voice] 聞き取りを始められない", error);
  }
}

export function startListening(onHeard: (text: string) => void): () => void {
  const Recognizer = findRecognizerClass();
  if (!Recognizer) return stopListening;
  stopListening();
  const recognizer = new Recognizer();
  recognizer.lang = LANG;
  recognizer.continuous = true;
  recognizer.interimResults = false;
  recognizer.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal && text) onHeard(text);
    }
  };
  recognizer.onerror = (event) => {
    if (!PERMISSION_ERRORS.has(event.error)) return;
    console.warn("[voice] マイクか音声認識が許可されていない", event.error);
    stopListening();
  };
  recognizer.onend = () => {
    if (active === recognizer) restartTimer = setTimeout(() => begin(recognizer), RESTART_DELAY_MS);
  };
  active = recognizer;
  begin(recognizer);
  return stopListening;
}

export function stopListening(): void {
  clearTimeout(restartTimer);
  const recognizer = active;
  active = null;
  recognizer?.abort();
}
