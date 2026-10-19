import assert from "node:assert/strict";
import test from "node:test";
import { dateTime, duration, sessionStatus } from "./recordFormat.ts";

process.env.TZ = "Asia/Tokyo";

test("日時は日本時間の月日と時刻で出す", () => {
  assert.equal(dateTime("2026-10-17T01:30:00Z"), "10/17 10:30");
});

test("1 分未満は秒だけで出す", () => {
  assert.equal(duration(0), "0 秒");
  assert.equal(duration(59), "59 秒");
});

test("1 分以上は分と秒で出す", () => {
  assert.equal(duration(60), "1 分 0 秒");
  assert.equal(duration(125), "2 分 5 秒");
});

test("セッションの状態は、はじめる前・見守り中・終わりの 3 つに分ける", () => {
  assert.equal(sessionStatus("created"), "はじめる前");
  for (const state of ["watching", "still", "stuck", "speaking", "cooldown", "checking"] as const) {
    assert.equal(sessionStatus(state), "見守り中");
  }
  assert.equal(sessionStatus("ended"), "終わり");
});
