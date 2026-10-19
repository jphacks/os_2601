import assert from "node:assert/strict";
import test from "node:test";
import { requestSignal } from "./requestSignal.ts";

test("呼び手が渡した signal を時間切れの signal で上書きせず、呼び手が止めれば止まる", () => {
  const caller = new AbortController();
  const signal = requestSignal(60_000, caller.signal);
  assert.equal(signal.aborted, false);
  caller.abort();
  assert.equal(signal.aborted, true);
});
