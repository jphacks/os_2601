import type { Persona } from "./personas";

export type SpeechProfile = {
  language: string;
  rate: number;
  pitch: number;
  preferredVoiceNames: readonly string[];
};

// OSに搭載された日本語音声だけを使う。実在人物の声を生成・複製しない。
// 音声名を指定すると、その端末の日本語音声から優先して選べる。
// Web Speech APIには性別の共通属性がなく、男性の声や抑揚は保証できない。
export const SPEECH_PROFILES: Record<Persona, SpeechProfile> = {
  teacher: { language: "ja-JP", rate: 1, pitch: 1, preferredVoiceNames: [] },
  ikemen: { language: "ja-JP", rate: 0.9, pitch: 0.85, preferredVoiceNames: [] },
};

export function selectJapaneseVoice(
  voices: readonly SpeechSynthesisVoice[],
  profile: SpeechProfile,
): SpeechSynthesisVoice | undefined {
  const japanese = voices.filter((voice) => voice.lang.replace(/_/g, "-").toLowerCase().startsWith("ja"));
  return (
    profile.preferredVoiceNames.map((name) => japanese.find((voice) => voice.name === name)).find(Boolean) ?? japanese[0]
  );
}
