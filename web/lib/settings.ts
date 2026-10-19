import type { Settings } from "./api";

export function normalizedSettings(settings: Settings): Settings {
  return { ...settings, persona: settings.persona ?? "teacher" };
}
