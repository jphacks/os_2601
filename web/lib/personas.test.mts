import assert from "node:assert/strict";
import test from "node:test";
import { endMessage, personaOf, personaOptions, voiceOf } from "./personas.ts";

test("サーバの終わりのセリフを使う", () => {
  const options = [{ id: "ikemen", display_name: "イケメン", end_message: "またな。" }];
  assert.equal(endMessage("ikemen", options), "またな。");
});

test("40 字までのセリフはサーバのものを使う", () => {
  const forty = "あ".repeat(40);
  assert.equal(endMessage("teacher", [{ id: "teacher", end_message: forty }]), forty);
});

test("サーバに無い・空・長すぎるセリフは、手元の既定に戻す", () => {
  const fallback = endMessage("teacher");
  assert.equal(endMessage("teacher", [{ id: "teacher", end_message: "  " }]), fallback);
  assert.equal(endMessage("teacher", [{ id: "teacher", end_message: "あ".repeat(41) }]), fallback);
  assert.equal(endMessage("teacher", "壊れた値"), fallback);
});

test("サーバが逆の順で返しても、画面の並びは先生・イケメンのまま", () => {
  const reversed = [
    { id: "ikemen", end_message: "またな。" },
    { id: "teacher", end_message: "またね。" },
  ];
  assert.deepEqual(personaOptions(reversed).map((option) => option.id), ["teacher", "ikemen"]);
});

test("人格ごとに声が決まる", () => {
  assert.equal(voiceOf("ikemen"), "handsome");
  assert.equal(voiceOf("teacher"), "teacher");
});

test("声から人格に戻すと元の人格になる", () => {
  for (const persona of ["teacher", "ikemen"] as const) assert.equal(personaOf(voiceOf(persona)), persona);
});
