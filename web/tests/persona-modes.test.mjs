import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// 既存のTypeScriptを使い、OS音声・カメラ・ネットワークを呼ばずに検査する。
function modules(overrides = {}, globals = {}) {
  const cache = new Map();
  const load = (filename) => {
    filename = path.resolve(webRoot, filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const compiledModule = { exports: {} };
    cache.set(filename, compiledModule);
    const require = (name) => {
      if (Object.hasOwn(overrides, name)) return overrides[name];
      if (name.endsWith(".json")) {
        const resolved = name.startsWith("@/") ? path.join(webRoot, name.slice(2)) : path.resolve(path.dirname(filename), name);
        return JSON.parse(readFileSync(resolved, "utf8"));
      }
      const resolved = name.startsWith("@/") ? path.join(webRoot, name.slice(2)) : path.resolve(path.dirname(filename), name);
      return load(`${resolved}.ts`);
    };
    const output = ts.transpileModule(readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    vm.runInNewContext(output, {
      module: compiledModule, exports: compiledModule.exports, require, console: { warn() {} }, setTimeout, clearTimeout, URLSearchParams,
      process: { env: {} }, ...globals,
    }, { filename });
    return compiledModule.exports;
  };
  return load;
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("only the two supported personas survive legacy values and metadata", () => {
  const { normalizePersona, personaOptions, endMessage } = modules()("lib/personas.ts");
  assert.equal(normalizePersona("ikemen"), "ikemen");
  for (const value of ["friend", "sister", "unknown", undefined, null]) assert.equal(normalizePersona(value), "teacher");
  const options = personaOptions([{ id: "friend", end_message: "old" }, { id: "ikemen", end_message: "今日はここまでだ。" }]);
  assert.equal(JSON.stringify(options.map((item) => [item.id, item.display_name])), JSON.stringify([["teacher", "家庭教師"], ["ikemen", "イケメン"]]));
  assert.equal(endMessage("ikemen", options), "今日はここまでだ。");
  for (const option of personaOptions()) {
    assert.ok(Array.from(option.end_message).length <= 40);
    assert.ok(Array.from(option.end_message).length <= 60);
  }
  assert.notEqual(endMessage("ikemen", [{ id: "ikemen", end_message: "長".repeat(41) }]), "長".repeat(41));
});

function speechEnvironment({ voices = [{ name: "日本語標準", lang: "ja-JP" }], engineChanges = {}, utteranceClass } = {}) {
  const spoken = [];
  const events = new Map();
  const engine = {
    getVoices: () => voices,
    addEventListener: (name, callback) => events.set(name, callback),
    removeEventListener: (name) => events.delete(name),
    cancel() {},
    speak(utterance) { spoken.push(utterance); queueMicrotask(() => utterance.onend?.()); },
    ...engineChanges,
  };
  class Utterance {
    constructor(text) { this.text = text; this.rate = 1; this.pitch = 1; }
  }
  const load = modules({}, { window: { speechSynthesis: engine }, SpeechSynthesisUtterance: utteranceClass ?? Utterance });
  return { api: load("lib/speech.ts"), load, spoken, events, engine };
}

test("ikemen reads the exact text with the adjustable slower/lower Japanese profile", async () => {
  const env = speechEnvironment();
  const message = "移項した項の符号を見てみよう。";
  await env.api.speak(message, "ikemen");
  assert.equal(env.spoken[0].text, message);
  assert.equal(env.spoken[0].lang, "ja-JP");
  assert.equal(env.spoken[0].rate, 0.9);
  assert.equal(env.spoken[0].pitch, 0.85);
  const profiles = env.load("lib/speech-profile.ts").SPEECH_PROFILES;
  profiles.ikemen.rate = 0.95;
  await env.api.speak(message, "ikemen");
  assert.equal(env.spoken[1].rate, 0.95);
  await env.api.speak(message, "teacher");
  assert.equal(env.spoken[2].rate, 1);
  assert.equal(env.spoken[2].pitch, 1);
});

test("preferred installed Japanese voice is selected, and absent voices use neutral defaults", async () => {
  const env = speechEnvironment({ voices: [{ name: "English", lang: "en-US" }, { name: "日本語一", lang: "ja_JP" }, { name: "日本語二", lang: "ja-JP" }] });
  env.load("lib/speech-profile.ts").SPEECH_PROFILES.ikemen.preferredVoiceNames = ["English", "日本語二"];
  await env.api.speak("符号を見てみよう。", "ikemen");
  assert.equal(env.spoken[0].voice.name, "日本語二");
  const fallback = speechEnvironment({ voices: [{ name: "English", lang: "en-US" }] });
  await fallback.api.speak("符号を見てみよう。", "ikemen");
  assert.equal(fallback.spoken[0].voice, undefined);
  assert.equal(fallback.spoken[0].rate, 1);
  assert.equal(fallback.spoken[0].pitch, 1);
});

test("late voices are re-evaluated and cancellation prevents stale speech", async () => {
  let voices = [];
  const env = speechEnvironment({ engineChanges: { getVoices: () => voices } });
  const pending = env.api.speak("古いヒント。", "ikemen");
  env.api.stopSpeaking();
  voices = [{ name: "遅れて読み込まれた日本語", lang: "ja-JP" }];
  env.events.get("voiceschanged")();
  await pending;
  assert.equal(env.spoken.length, 0);
  await env.api.speak("新しいヒント。", "ikemen");
  assert.equal(env.spoken[0].voice.name, "遅れて読み込まれた日本語");
});

test("missing synthesis, constructors, and throwing APIs do not crash", async () => {
  for (const globals of [{}, { window: {} }, { window: { speechSynthesis: {} } }]) {
    const api = modules({}, globals)("lib/speech.ts");
    assert.doesNotThrow(() => api.unlockSpeech());
    assert.doesNotThrow(() => api.stopSpeaking());
    await api.speak("字幕は残る。", "ikemen");
  }
  const env = speechEnvironment({ engineChanges: {
    getVoices() { throw new Error("not available"); }, cancel() { throw new Error("not available"); }, speak() { throw new Error("not available"); },
  } });
  assert.doesNotThrow(() => env.api.unlockSpeech());
  assert.doesNotThrow(() => env.api.stopSpeaking());
  await env.api.speak("字幕は残る。", "ikemen");
});

test("unsupported pitch/rate falls back without modifying the spoken text", async () => {
  class LimitedUtterance {
    constructor(text) { this.text = text; }
    set rate(value) { if (value !== 1) throw new Error("rate unsupported"); }
    set pitch(value) { if (value !== 1) throw new Error("pitch unsupported"); }
  }
  const env = speechEnvironment({ utteranceClass: LimitedUtterance });
  await env.api.speak("字幕と同じ文。", "ikemen");
  assert.equal(env.spoken[0].text, "字幕と同じ文。");
});

function deviceEnvironment({
  initialPersona = "teacher", initialProblemNo = 1, endingProblemNo = initialProblemNo, problems = [], patch,
  cameraStart = async () => {}, manualHint, next = async () => ({ state: "watching", current_problem_no: 2 }),
} = {}) {
  const slots = [], effects = [];
  let cursor = 0;
  const react = {
    Suspense: "Suspense",
    useRef(initial) { const index = cursor++; return slots[index] ??= { current: initial }; },
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (next) => { slots[index] = typeof next === "function" ? next(slots[index]) : next; }];
    },
    useEffect(callback, deps) {
      const index = cursor++;
      const previous = slots[index];
      if (!previous || deps.some((value, i) => value !== previous.deps[i])) effects.push(() => {
        previous?.cleanup?.(); slots[index] = { deps, cleanup: callback() };
      });
    },
  };
  const component = (name) => ({ [name]: function () {} })[name];
  const components = {};
  for (const name of ["Buttons", "Caption", "HeardBubble", "Character", "Header", "SecondsPicker", "ProblemText", "VideoFrame"]) components[name] = component(name);
  const spoken = [], updates = [];
  const loop = { callbacks: null,
    startSession(_video, _id, _token, callbacks, persona) { loop.callbacks = callbacks; loop.persona = persona; return () => {}; },
    updateSessionPersona(id, persona) { updates.push({ id, persona }); },
    requestManualHint: manualHint,
    advance: next,
    end: async () => loop.callbacks.onState({ state: "ended", current_problem_no: endingProblemNo, still_seconds: 0 }),
  };
  const api = {
    ApiError: class extends Error {},
    getSession: async () => ({ session_id: "s", current_problem_no: initialProblemNo, problems, mode: "live", settings: { stuck_seconds: 20, persona: initialPersona },
      persona_options: [{ id: "teacher", display_name: "家庭教師", end_message: "今日の取り組みを記録で振り返りましょう。" }, { id: "ikemen", display_name: "イケメン", end_message: "今日の頑張り、記録で見てみようぜ。" }] }),
    patchSettings: patch ?? (async (_id, _token, body) => ({ settings: { stuck_seconds: 20, persona: body.persona }, state: "created" })),
  };
  const overrides = {
    react,
    "react/jsx-runtime": { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }) },
    "next/navigation": { useSearchParams: () => new URLSearchParams("s=s&t=test") },
    "@/lib/api": api,
    "@/lib/camera": { startCamera: cameraStart, stopCamera() {} },
    "@/lib/loop": loop,
    "@/lib/speech": { speak: async (text, persona) => spoken.push({ text, persona }), stopSpeaking() {}, unlockSpeech() {} },
    "@/lib/voice": { primeListening() {}, stopListening() {}, voiceStatus: () => "" },
  };
  for (const file of ["Buttons", "Caption", "Character", "Header", "SecondsPicker", "ProblemText", "VideoFrame"]) overrides[`./_components/${file}`] = { ...components, nearestChoice: (value) => value };
  const load = modules(overrides, { window: { confirm: () => true } });
  const page = load("app/device/page.tsx");
  const Device = page.default().props.children.type;
  function render() { cursor = 0; return Device(); }
  function find(tree, type) {
    if (!tree || typeof tree !== "object") return null;
    if (tree.type === type) return tree;
    for (const child of [tree.props?.children].flat(Infinity)) { const found = find(child, type); if (found) return found; }
    return null;
  }
  const first = render();
  find(first, components.VideoFrame).props.videoRef.current = {};
  while (effects.length) effects.shift()();
  return { render, find, components, spoken, updates, loop,
    select: () => find(render(), "select"),
    buttons: () => find(render(), components.Buttons).props,
    caption: () => find(render(), components.Caption).props.text,
    problemText: () => find(render(), components.ProblemText).props.text,
    unmount: () => slots.forEach((slot) => slot?.cleanup?.()),
  };
}

test("device exposes two choices, waits for confirmation, and keeps the old selection on failure", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ patch: () => pending.promise });
  assert.equal(env.select().props.disabled, true);
  await flush();
  assert.equal(env.select().props.value, "teacher");
  assert.equal(env.select().props.children.length, 2);
  env.select().props.onChange({ target: { value: "ikemen" } });
  assert.equal(env.select().props.value, "teacher");
  assert.equal(env.select().props.disabled, true);
  pending.reject(new Error("network failure"));
  await flush();
  assert.equal(env.select().props.value, "teacher");
  assert.equal(env.updates.length, 0);
  assert.equal(env.select().props.disabled, false);
});

test("confirmed choice reaches the loop; ending displays and speaks exactly the configured message once", async () => {
  const env = deviceEnvironment();
  await flush();
  env.select().props.onChange({ target: { value: "ikemen" } });
  await flush();
  assert.equal(env.select().props.value, "ikemen");
  assert.equal(env.updates[0].persona, "ikemen");
  await env.buttons().onStart();
  assert.equal(env.loop.persona, "ikemen");
  await env.buttons().onEnd();
  assert.equal(env.caption(), "今日の頑張り、記録で見てみようぜ。");
  assert.equal(env.spoken[0].text, env.caption());
  assert.equal(env.spoken[0].persona, "ikemen");
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  assert.equal(env.spoken.length, 1);
});

test("a settings response arriving after ending cannot replace the confirmed persona or caption", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ patch: () => pending.promise });
  await flush();
  await env.buttons().onStart();
  env.loop.callbacks.onState({ state: "watching", current_problem_no: 1, still_seconds: 0 });
  env.select().props.onChange({ target: { value: "ikemen" } });
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  const caption = env.caption();
  pending.resolve({ settings: { stuck_seconds: 20, persona: "ikemen" }, state: "watching" });
  await flush();
  assert.equal(env.select().props.value, "teacher");
  assert.equal(env.caption(), caption);
  assert.equal(env.spoken[0].text, caption);
  assert.equal(env.updates.length, 0);
});

test("legacy friend and an unmounted settings request cannot resurrect the removed mode", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ initialPersona: "friend", patch: () => pending.promise });
  await flush();
  assert.equal(env.select().props.value, "teacher");
  env.select().props.onChange({ target: { value: "ikemen" } });
  env.unmount();
  pending.resolve({ settings: { stuck_seconds: 20, persona: "ikemen" }, state: "created" });
  await flush();
  assert.equal(env.updates.length, 0);
});

test("starting and saving a persona cannot race before a React rerender", async () => {
  const camera = deferred();
  let patches = 0;
  const env = deviceEnvironment({
    cameraStart: () => camera.promise,
    patch: async () => { patches += 1; return { settings: { persona: "ikemen", stuck_seconds: 20 }, state: "created" }; },
  });
  await flush();
  const staleSelect = env.select();
  const starting = env.buttons().onStart();
  staleSelect.props.onChange({ target: { value: "ikemen" } });
  assert.equal(patches, 0);
  camera.resolve();
  await starting;
  assert.equal(env.loop.persona, "teacher");

  const pending = deferred();
  const saving = deviceEnvironment({ patch: () => pending.promise });
  await flush();
  const staleButtons = saving.buttons();
  saving.select().props.onChange({ target: { value: "ikemen" } });
  await staleButtons.onStart();
  assert.equal(saving.loop.callbacks, null);
  pending.resolve({ settings: { persona: "ikemen", stuck_seconds: 20 }, state: "created" });
  await flush();
  await saving.buttons().onStart();
  assert.equal(saving.loop.persona, "ikemen");
});

test("the parsed problem begins empty and restores only the saved current problem", async () => {
  const empty = deviceEnvironment();
  assert.equal(empty.problemText(), null);
  await flush();
  assert.equal(empty.problemText(), null);
  const saved = deviceEnvironment({ initialProblemNo: 2, problems: [
    { problem_no: 1, problem_text: "前の問題" },
    { problem_no: 2, problem_text: "二つの式を連立して解きなさい。" },
  ] });
  await flush();
  assert.equal(saved.problemText(), "二つの式を連立して解きなさい。");
  const header = saved.find(saved.render(), saved.components.Header);
  assert.equal(header.props.mode, "live");
  assert.equal(header.props.info, undefined);
});

test("manual and automatic hints update the parsed problem independently of speech", async () => {
  const env = deviceEnvironment({ manualHint: async () => ({
    problem_no: 1, state: "speaking", speech: "移項した項を見てみよう。", display: "移項した項を見てみよう。",
    problem_text: "一次方程式を解きなさい。",
  }) });
  await flush();
  await env.buttons().onStart();
  await env.buttons().onHint();
  assert.equal(env.problemText(), "一次方程式を解きなさい。");
  assert.equal(env.caption(), "移項した項を見てみよう。");
  env.loop.callbacks.onHint({
    problem_no: 1, speech: "係数を見てみよう。", display: "係数を見てみよう。", problem_text: "写真から読んだ方程式。",
  });
  assert.equal(env.problemText(), "写真から読んだ方程式。");
  assert.equal(env.caption(), "係数を見てみよう。");
  env.loop.callbacks.onHint({ problem_no: 1, speech: null, display: "表示しない文", problem_text: "訂正された問題文。" });
  assert.equal(env.problemText(), "訂正された問題文。");
  assert.equal(env.caption(), "係数を見てみよう。");
});

test("advancing clears the old problem, and the long-lived loop callback retains the next problem", async () => {
  const env = deviceEnvironment({ problems: [{ problem_no: 1, problem_text: "最初の問題。" }] });
  await flush();
  await env.buttons().onStart();
  const initialCallbacks = env.loop.callbacks;
  assert.equal(env.problemText(), "最初の問題。");
  await env.buttons().onNext();
  assert.equal(env.problemText(), null);
  initialCallbacks.onHint({ problem_no: 2, speech: "係数を見てみよう。", display: "係数を見てみよう。", problem_text: "次の問題。" });
  initialCallbacks.onState({ state: "watching", current_problem_no: 2, still_seconds: 0 });
  assert.equal(env.problemText(), "次の問題。");
  initialCallbacks.onState({ state: "watching", current_problem_no: 2, still_seconds: 1 });
  assert.equal(env.problemText(), "次の問題。");
  initialCallbacks.onHint({ problem_no: 1, speech: "古いヒント", display: "古いヒント", problem_text: "古い問題。" });
  initialCallbacks.onState({ state: "watching", current_problem_no: 1, still_seconds: 0 });
  assert.equal(env.problemText(), "次の問題。");
  initialCallbacks.onState({ state: "watching", current_problem_no: 3, still_seconds: 0 });
  assert.equal(env.problemText(), null);
});

test("a delayed manual response cannot restore the previous problem after advancing", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ manualHint: () => pending.promise });
  await flush();
  await env.buttons().onStart();
  const hinting = env.buttons().onHint();
  await env.buttons().onNext();
  env.loop.callbacks.onHint({ problem_no: 2, speech: "次のヒント。", display: "次のヒント。", problem_text: "次の問題。" });
  pending.resolve({ problem_no: 1, state: "speaking", speech: "古いヒント。", display: "古いヒント。", problem_text: "前の問題。" });
  await hinting;
  assert.equal(env.problemText(), "次の問題。");
  assert.equal(env.caption(), "次のヒント。");
});

test("ending and unmounting reject delayed parsed problem updates", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ manualHint: () => pending.promise, problems: [{ problem_no: 1, problem_text: "現在の問題。" }] });
  await flush();
  await env.buttons().onStart();
  const hinting = env.buttons().onHint();
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  const endingCaption = env.caption();
  env.loop.callbacks.onHint({ problem_no: 1, speech: "遅い文。", display: "遅い文。", problem_text: "遅い問題。" });
  pending.resolve({ problem_no: 1, state: "speaking", speech: "遅い文。", display: "遅い文。", problem_text: "遅い問題。" });
  await hinting;
  assert.equal(env.problemText(), "現在の問題。");
  assert.equal(env.caption(), endingCaption);
  assert.equal(env.spoken[0].text, endingCaption);

  const detached = deviceEnvironment({ problems: [{ problem_no: 1, problem_text: "保存された問題。" }] });
  await flush();
  await detached.buttons().onStart();
  const callbacks = detached.loop.callbacks;
  detached.unmount();
  callbacks.onHint({ problem_no: 1, speech: null, problem_text: "破棄後の問題。" });
  assert.equal(detached.problemText(), "保存された問題。");
});

test("ending a resumed session before its first signal preserves the current problem and ends once", async () => {
  const env = deviceEnvironment({ initialPersona: "ikemen", initialProblemNo: 2, endingProblemNo: 1, problems: [
    { problem_no: 1, problem_text: "前の問題。" },
    { problem_no: 2, problem_text: "再開した現在の問題。" },
  ] });
  await flush();
  await env.buttons().onStart();
  await env.buttons().onEnd();
  assert.equal(env.buttons().state, "ended");
  assert.equal(env.problemText(), "再開した現在の問題。");
  assert.equal(env.caption(), "今日の頑張り、記録で見てみようぜ。");
  assert.equal(env.spoken[0].text, env.caption());
  assert.equal(env.spoken[0].persona, "ikemen");
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  env.loop.callbacks.onState({ state: "watching", current_problem_no: 1, still_seconds: 0 });
  assert.equal(env.buttons().state, "ended");
  assert.equal(env.problemText(), "再開した現在の問題。");
  assert.equal(env.spoken.length, 1);
});
