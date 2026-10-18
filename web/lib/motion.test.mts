import assert from "node:assert/strict";
import test from "node:test";
import { differenceIgnoringBrightness, median } from "./motion.ts";

const frame = (values: number[]) => Float32Array.from(values);

test("同じ画面なら差分は 0", () => {
  assert.equal(differenceIgnoringBrightness(frame([10, 20, 30, 40]), frame([10, 20, 30, 40])), 0);
});

test("画面全体が同じだけ明るくなっても、動きとは数えない", () => {
  assert.equal(differenceIgnoringBrightness(frame([60, 70, 80, 90]), frame([10, 20, 30, 40])), 0);
});

test("一部だけ変わると、その分だけ動きになる", () => {
  const moved = differenceIgnoringBrightness(frame([10, 20, 30, 140]), frame([10, 20, 30, 40]));
  assert.equal(moved, 25);
});

test("明るさの変化と手の動きが重なっても、手の動きだけが残る", () => {
  const brighterAndMoved = differenceIgnoringBrightness(frame([60, 70, 80, 190]), frame([10, 20, 30, 40]));
  const movedOnly = differenceIgnoringBrightness(frame([10, 20, 30, 140]), frame([10, 20, 30, 40]));
  assert.equal(brighterAndMoved, movedOnly);
});

test("median は外れ値 1 つに引きずられない", () => {
  assert.equal(median([0.01, 0.9, 0.02]), 0.02);
});
