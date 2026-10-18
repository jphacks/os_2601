import assert from "node:assert/strict";
import test from "node:test";
import { endMessage, personaOptions } from "./personas.ts";

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
