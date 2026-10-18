import type { VoiceCharacter } from "./api";

export type Persona = "teacher" | "ikemen";

export type PersonaOption = { id: Persona; display_name: string; end_message: string };

// 古いモックにメタデータがない場合だけ使う。通常はサーバーの人格設定を使う。
const FALLBACK_OPTIONS: readonly PersonaOption[] = [
  {
    id: "teacher",
    display_name: "家庭教師",
    end_message: "今日もよく頑張りました。できるようになったことを記録で振り返ってみましょう。",
  },
  {
    id: "ikemen",
    display_name: "イケメン",
    end_message: "今日はここまで。よくやったじゃん。頑張った証拠、記録で確かめてみな。",
  },
];

export function personaOptions(value: unknown): PersonaOption[] {
  const options = Array.isArray(value) ? value : [];
  return FALLBACK_OPTIONS.map((fallback) => {
    const candidate = options.find((option) => option?.id === fallback.id);
    const message = candidate?.end_message;
    return {
      id: fallback.id,
      display_name: fallback.display_name,
      end_message:
        typeof message === "string" && message.trim() && Array.from(message).length <= 40
          ? message
          : fallback.end_message,
    };
  });
}

export function endMessage(persona: Persona, options?: unknown): string {
  return personaOptions(options).find((option) => option.id === persona)!.end_message;
}

export function voiceOf(persona: Persona): VoiceCharacter {
  return persona === "ikemen" ? "handsome" : "teacher";
}

export function personaOf(voice: VoiceCharacter): Persona {
  return voice === "handsome" ? "ikemen" : "teacher";
}
