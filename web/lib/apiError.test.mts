import assert from "node:assert/strict";
import test from "node:test";
import { ApiError } from "./apiError.ts";

test("エラーの本文から状態コードとエラーコードを取り出す", async () => {
  const response = Response.json({ error: { code: "UNAUTHORIZED", message: "鍵が違う" } }, { status: 401 });
  const error = await ApiError.fromResponse(response);
  assert.equal(error.status, 401);
  assert.equal(error.code, "UNAUTHORIZED");
  assert.equal(error.message, "API 401 UNAUTHORIZED: 鍵が違う");
});

test("本文が JSON でなければ UNKNOWN にする", async () => {
  const error = await ApiError.fromResponse(new Response("<html>Bad Gateway</html>", { status: 502 }));
  assert.equal(error.status, 502);
  assert.equal(error.code, "UNKNOWN");
  assert.equal(error.message, "API 502 UNKNOWN");
});

test("JSON でも error が無ければ UNKNOWN にする", async () => {
  const error = await ApiError.fromResponse(Response.json({ detail: "Not Found" }, { status: 404 }));
  assert.equal(error.code, "UNKNOWN");
  assert.equal(error.message, "API 404 UNKNOWN");
});

test("Error として扱え、名前で見分けられる", () => {
  const error = new ApiError(503, "HINT_UNAVAILABLE");
  assert.ok(error instanceof Error);
  assert.equal(error.name, "ApiError");
});
