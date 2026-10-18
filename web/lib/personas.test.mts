import assert from "node:assert/strict";
import test from "node:test";
import { endMessage, personaOptions } from "./personas.ts";

test("サーバの終わりのセリフを使う", () => {
  const options = [{ id: "ikemen", display_name: "イケメン", end_message: "またな。" }];
  assert.equal(endMessage("ikemen", options), "またな。");
});

test("サーバに無い・空・長すぎるセリフは、手元の既定に戻す", () => {
  const fallback = endMessage("teacher");
  assert.equal(endMessage("teacher", [{ id: "teacher", end_message: "  " }]), fallback);
  assert.equal(endMessage("teacher", [{ id: "teacher", end_message: "あ".repeat(41) }]), fallback);
  assert.equal(endMessage("teacher", "壊れた値"), fallback);
});

test("人格は先生とイケメンの 2 つで、順番は変わらない", () => {
  assert.deepEqual(personaOptions([]).map((option) => option.id), ["teacher", "ikemen"]);
});
