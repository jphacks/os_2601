import assert from "node:assert/strict";
import test from "node:test";
import type { Settings } from "./api.ts";
import { normalizedSettings } from "./settings.ts";

test("persona が undefined で上書きされた設定も先生に戻す（本物とモックで設定の応答をそろえる）", () => {
  const overwritten = { stuck_seconds: 20, cooldown_seconds: 60, max_level: 2, persona: undefined };
  assert.deepEqual(normalizedSettings(overwritten as unknown as Settings), {
    stuck_seconds: 20,
    cooldown_seconds: 60,
    max_level: 2,
    persona: "teacher",
  });
});
