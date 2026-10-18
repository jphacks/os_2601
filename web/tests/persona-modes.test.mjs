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
  initialPersona = "teacher", initialState = "watching", initialProblemNo = 1, endingProblemNo = initialProblemNo, problems = [], patch,
  cameraStart = async () => {}, manualHint, next = async () => ({ state: "watching", current_problem_no: 2 }),
  readRecord,
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
  for (const name of ["Buttons", "Caption", "HeardBubble", "Character", "Header", "RecordSheet", "SecondsPicker", "ProblemText", "VideoFrame"]) components[name] = component(name);
  const spoken = [], updates = [], settingsRequests = [];
  let sessionReads = 0;
  const loop = { callbacks: null,
    startSession(_video, _id, _token, callbacks, persona) { loop.callbacks = callbacks; loop.persona = persona; return () => {}; },
    updateSessionPersona(id, persona) { updates.push({ id, persona }); },
    requestManualHint: manualHint,
    advance: next,
    end: async () => loop.callbacks.onState({ state: "ended", current_problem_no: endingProblemNo, still_seconds: 0 }),
  };
  const api = {
    ApiError: class extends Error {},
    getSession: async () => {
      sessionReads += 1;
      if (sessionReads > 1 && readRecord) return readRecord();
      return { session_id: "s", state: initialState, current_problem_no: initialProblemNo, problems, mode: "live", settings: { stuck_seconds: 20, persona: initialPersona },
        persona_options: [{ id: "teacher", display_name: "家庭教師", end_message: "今日の取り組みを記録で振り返りましょう。" }, { id: "ikemen", display_name: "イケメン", end_message: "今日の頑張り、記録で見てみようぜ。" }] };
    },
    patchSettings: async (...args) => {
      settingsRequests.push(args);
      return patch ? patch(...args) : { settings: { stuck_seconds: 20, persona: args[2].persona }, state: "created" };
    },
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
    "next/image": { default: component("Image") },
    "./character.png": { default: { src: "/character.png" } },
    "./teacher.png": { default: { src: "/teacher.png" } },
  };
  for (const file of ["Buttons", "Caption", "Header", "RecordSheet", "SecondsPicker", "ProblemText", "VideoFrame"]) overrides[`./_components/${file}`] = { ...components, nearestChoice: (value) => value };
  const load = modules(overrides, { window: { confirm: () => true } });
  components.Character = load("app/device/_components/Character.tsx").Character;
  components.CharacterPicker = load("app/device/_components/CharacterPicker.tsx").CharacterPicker;
  overrides["./_components/Character"] = { Character: components.Character };
  overrides["./_components/CharacterPicker"] = { CharacterPicker: components.CharacterPicker };
  const characters = load("app/device/_components/characters.ts").CHARACTERS;
  const page = load("app/device/page.tsx");
  const Device = page.default().props.children.type;
  function render() { cursor = 0; return Device(); }
  function find(tree, type) {
    if (!tree || typeof tree !== "object") return null;
    if (tree.type === type) return tree;
    for (const child of [tree.props?.children].flat(Infinity)) { const found = find(child, type); if (found) return found; }
    return null;
  }
  function findAll(tree, type) {
    if (!tree || typeof tree !== "object") return [];
    return [
      ...(tree.type === type ? [tree] : []),
      ...[tree.props?.children].flat(Infinity).flatMap((child) => findAll(child, type)),
    ];
  }
  const first = render();
  find(first, components.VideoFrame).props.videoRef.current = {};
  while (effects.length) effects.shift()();
  const picker = () => find(render(), components.CharacterPicker);
  const pickerButtons = () => findAll(components.CharacterPicker(picker().props), "button");
  return { render, find, components, spoken, updates, settingsRequests, loop,
    picker,
    pickerButtons,
    choose: (id) => pickerButtons()[characters.findIndex((character) => character.id === id)].props.onClick(),
    imageSource: () => {
      const character = find(render(), components.Character);
      return components.Character(character.props).props.src.src;
    },
    buttons: () => find(render(), components.Buttons).props,
    caption: () => find(render(), components.Caption).props.text,
    problemText: () => find(render(), components.ProblemText).props.text,
    recordSheet: () => find(render(), components.RecordSheet),
    recordButton: () => findAll(render(), "button").find((button) => ["記録を見る", "読み込み中…"].includes(button.props.children)),
    recordError: () => findAll(render(), "p").find((paragraph) => paragraph.props.children === "記録を読めませんでした"),
    sessionReads: () => sessionReads,
    unmount: () => slots.forEach((slot) => slot?.cleanup?.()),
  };
}

test("device exposes two choices, waits for confirmation, and keeps the old selection on failure", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ patch: () => pending.promise });
  assert.equal(env.picker().props.disabled, true);
  await flush();
  assert.equal(env.picker().props.value, "teacher");
  assert.equal(env.pickerButtons().length, 2);
  assert.equal(env.imageSource(), "/teacher.png");
  env.choose("handsome");
  assert.equal(env.picker().props.value, "teacher");
  assert.equal(env.imageSource(), "/teacher.png");
  assert.equal(env.picker().props.disabled, true);
  pending.reject(new Error("network failure"));
  await flush();
  assert.equal(env.picker().props.value, "teacher");
  assert.equal(env.imageSource(), "/teacher.png");
  assert.equal(env.updates.length, 0);
  assert.equal(env.picker().props.disabled, false);
});

test("saved personas restore the matching real character image and pressed picker button", async () => {
  for (const [persona, character, image] of [
    ["teacher", "teacher", "/teacher.png"],
    ["ikemen", "handsome", "/character.png"],
  ]) {
    const env = deviceEnvironment({ initialPersona: persona });
    await flush();
    assert.equal(env.picker().props.value, character);
    assert.equal(env.imageSource(), image);
    assert.equal(env.pickerButtons()[0].props["aria-pressed"], persona === "ikemen");
    assert.equal(env.pickerButtons()[1].props["aria-pressed"], persona === "teacher");
    assert.equal(env.settingsRequests.length, 0);
  }
});

test("real picker is disabled while loading, saving, or ended and page guards prevent extra API calls", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ patch: () => pending.promise });
  assert.equal(env.components.CharacterPicker(env.picker().props).props.disabled, true);
  assert.ok(env.pickerButtons().every((button) => button.props.disabled));
  env.choose("handsome");
  assert.equal(env.settingsRequests.length, 0);
  await flush();
  env.choose("handsome");
  assert.equal(env.settingsRequests.length, 1);
  assert.ok(env.pickerButtons().every((button) => button.props.disabled));
  env.choose("teacher");
  assert.equal(env.settingsRequests.length, 1);
  assert.equal(env.imageSource(), "/teacher.png");
  pending.resolve({ settings: { stuck_seconds: 20, persona: "ikemen" }, state: "created" });
  await flush();
  assert.equal(env.picker().props.value, "handsome");
  assert.equal(env.imageSource(), "/character.png");
  await env.buttons().onStart();
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  assert.ok(env.pickerButtons().every((button) => button.props.disabled));
  env.choose("teacher");
  assert.equal(env.settingsRequests.length, 1);
  assert.equal(env.picker().props.value, "handsome");
  assert.equal(env.imageSource(), "/character.png");
});

test("confirmed choice reaches the loop; ending displays and speaks exactly the configured message once", async () => {
  const env = deviceEnvironment();
  await flush();
  env.choose("handsome");
  await flush();
  assert.equal(env.picker().props.value, "handsome");
  assert.equal(env.imageSource(), "/character.png");
  assert.equal(env.settingsRequests[0][2].persona, "ikemen");
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
  env.choose("handsome");
  env.loop.callbacks.onState({ state: "ended", current_problem_no: 1, still_seconds: 0 });
  const caption = env.caption();
  pending.resolve({ settings: { stuck_seconds: 20, persona: "ikemen" }, state: "watching" });
  await flush();
  assert.equal(env.picker().props.value, "teacher");
  assert.equal(env.imageSource(), "/teacher.png");
  assert.equal(env.caption(), caption);
  assert.equal(env.spoken[0].text, caption);
  assert.equal(env.updates.length, 0);
});

test("legacy friend and an unmounted settings request cannot resurrect the removed mode", async () => {
  const pending = deferred();
  const env = deviceEnvironment({ initialPersona: "friend", patch: () => pending.promise });
  await flush();
  assert.equal(env.picker().props.value, "teacher");
  assert.equal(env.imageSource(), "/teacher.png");
  env.choose("handsome");
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
  const staleButton = env.pickerButtons()[0];
  const starting = env.buttons().onStart();
  staleButton.props.onClick();
  assert.equal(patches, 0);
  camera.resolve();
  await starting;
  assert.equal(env.loop.persona, "teacher");

  const pending = deferred();
  const saving = deviceEnvironment({ patch: () => pending.promise });
  await flush();
  const staleButtons = saving.buttons();
  saving.choose("handsome");
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

test("startup problem reading updates the text without changing the hint or speaking again", async () => {
  const env = deviceEnvironment({ initialPersona: "ikemen" });
  await flush();
  await env.buttons().onStart();
  const caption = env.caption();
  env.loop.callbacks.onProblem("開始時に読み取った問題文。");
  assert.equal(env.problemText(), "開始時に読み取った問題文。");
  assert.equal(env.caption(), caption);
  assert.equal(env.spoken.length, 0);
  await env.buttons().onEnd();
  env.loop.callbacks.onProblem("終了後に届いた問題文。");
  assert.equal(env.problemText(), "開始時に読み取った問題文。");
  assert.equal(env.spoken.length, 1);
});

test("reloading an ended session restores its persona ending and exposes records without restarting audio", async () => {
  const env = deviceEnvironment({ initialPersona: "ikemen", initialState: "ended" });
  await flush();
  assert.equal(env.buttons().state, "ended");
  assert.equal(env.picker().props.disabled, true);
  assert.equal(env.picker().props.value, "handsome");
  assert.equal(env.imageSource(), "/character.png");
  assert.equal(env.caption(), "今日の頑張り、記録で見てみようぜ。");
  assert.equal(env.recordButton().props.children, "記録を見る");
  assert.equal(env.spoken.length, 0);
  await env.buttons().onStart();
  assert.equal(env.loop.callbacks, null);
});

test("records fetch a fresh session once, expose loading, and close back to the ending", async () => {
  const pending = deferred();
  const fresh = { session_id: "s", state: "ended", problems: [{ problem_no: 1, problem_text: "最新の問題文。" }] };
  const env = deviceEnvironment({ initialState: "ended", readRecord: () => pending.promise });
  await flush();
  const button = env.recordButton();
  const loading = button.props.onClick();
  await button.props.onClick();
  assert.equal(env.sessionReads(), 2);
  assert.equal(env.recordButton().props.children, "読み込み中…");
  assert.equal(env.recordButton().props.disabled, true);
  pending.resolve(fresh);
  await loading;
  assert.equal(env.recordSheet().props.session, fresh);
  env.recordSheet().props.onClose();
  assert.equal(env.recordSheet(), null);
  assert.equal(env.buttons().state, "ended");
  assert.equal(env.spoken.length, 0);
});

test("record errors remain retryable and detached responses cannot reopen the record sheet", async () => {
  const pending = deferred();
  let attempts = 0;
  const env = deviceEnvironment({ initialState: "ended", readRecord: () => {
    attempts += 1;
    if (attempts === 1) return Promise.reject(new Error("temporarily unavailable"));
    return pending.promise;
  } });
  await flush();
  await env.recordButton().props.onClick();
  assert.ok(env.recordError());
  assert.equal(env.recordButton().props.disabled, false);
  const loading = env.recordButton().props.onClick();
  env.unmount();
  pending.resolve({ session_id: "s", state: "ended", problems: [] });
  await loading;
  assert.equal(env.recordSheet(), null);
  assert.equal(env.sessionReads(), 3);
});

function fakeClock() {
  let now = 0, nextId = 0;
  const jobs = new Map();
  const schedule = (callback, delay, interval = 0) => {
    const id = ++nextId;
    jobs.set(id, { callback, at: now + delay, interval });
    return id;
  };
  return {
    setTimeout: (callback, delay) => schedule(callback, delay),
    clearTimeout: (id) => jobs.delete(id),
    setInterval: (callback, delay) => schedule(callback, delay, delay),
    clearInterval: (id) => jobs.delete(id),
    async tick(milliseconds) {
      const target = now + milliseconds;
      for (;;) {
        const next = [...jobs.entries()].filter(([, job]) => job.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        const [id, job] = next;
        now = job.at;
        if (job.interval) job.at += job.interval;
        else jobs.delete(id);
        job.callback();
        await flush();
      }
      now = target;
    },
  };
}

function loopEnvironment({ read, capture = async () => "jpeg" } = {}) {
  const clock = fakeClock();
  const problems = [], reads = [], spoken = [];
  let currentProblem = 1;
  const api = {
    postSignal: async () => ({ state: "watching", current_problem_no: currentProblem, still_seconds: 0, next_action: null }),
    postFrame: async () => ({ frame_id: "frame" }),
    readProblem: async (...args) => {
      reads.push(args);
      return read ? read(currentProblem) : { problem_no: currentProblem, problem_text: `読み取った問題${currentProblem}` };
    },
    postAdvance: async () => ({ state: "watching", current_problem_no: ++currentProblem }),
    postEnd: async () => ({ state: "ended" }),
  };
  const load = modules({
    "./api": api,
    "./camera": { captureFrame: capture, stopCamera() {} },
    "./motion": { startMotionLoop: () => () => {} },
    "./speech": { speak: async (text, persona) => spoken.push({ text, persona }), stopSpeaking() {} },
    "./voice": { startListening() {}, stopListening() {}, voiceStatus: () => "" },
  }, { ...clock, window: { location: { search: "" } } });
  const loop = load("lib/loop.ts");
  const stop = loop.startSession({}, "s", "test", {
    onState() {}, onHint() {}, onBrightness() {}, onConnection() {}, onHeard() {},
    onProblem: (text) => problems.push(text),
  }, "ikemen");
  return { loop, clock, problems, reads, spoken, stop };
}

test("the real loop reads three seconds after watching and rereads the next problem", async () => {
  const env = loopEnvironment();
  await env.clock.tick(1000);
  assert.equal(env.spoken[0].persona, "ikemen");
  await env.clock.tick(2999);
  assert.equal(env.reads.length, 0);
  await env.clock.tick(1);
  assert.equal(env.reads.length, 1);
  assert.deepEqual(env.problems, ["読み取った問題1"]);
  await env.loop.advance();
  await env.clock.tick(1000);
  assert.equal(env.reads.length, 2);
  assert.deepEqual(env.problems, ["読み取った問題1", "読み取った問題2"]);
  env.stop();
  await env.clock.tick(10000);
  assert.equal(env.reads.length, 2);
});

test("startup reading retries only once and never publishes a superseded problem", async () => {
  let attempts = 0;
  const retrying = loopEnvironment({ read: async () => {
    if (++attempts === 1) throw new Error("retryable");
    return { problem_no: 1, problem_text: "再試行した問題文。" };
  } });
  await retrying.clock.tick(7000);
  assert.equal(attempts, 2);
  assert.deepEqual(retrying.problems, ["再試行した問題文。"]);
  retrying.stop();

  const pending = deferred();
  const stale = loopEnvironment({ read: () => pending.promise });
  await stale.clock.tick(4000);
  await stale.loop.advance();
  pending.resolve({ problem_no: 1, problem_text: "前の問題文。" });
  await flush();
  assert.deepEqual(stale.problems, []);
  stale.stop();
});

test("ending during startup capture prevents a late read request and retry", async () => {
  const pending = deferred();
  const env = loopEnvironment({ capture: () => pending.promise });
  await env.clock.tick(4000);
  await env.loop.end();
  pending.resolve("late jpeg");
  await flush();
  await env.clock.tick(10000);
  assert.equal(env.reads.length, 0);
  assert.deepEqual(env.problems, []);
});
