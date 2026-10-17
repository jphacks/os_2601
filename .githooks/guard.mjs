import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, relative, sep } from "node:path";

const ROLES = ["takahashi", "b", "c", "d"];

const TAKAHASHI_ONLY = [
  /^\.github\//, /^\.githooks\//, /^\.claude\//, /^team\.json$/,
  /^package\.json$/, /^web\/package\.json$/, /^pnpm-lock\.yaml$/, /^pnpm-workspace\.yaml$/,
  /^CLAUDE\.md$/, /^AGENTS\.md$/,
];

const BASH_DENY_ALL = [
  [/git\s+push\b[^\n]*(--force\b|\s-f\b|--force-with-lease)/, "force push は禁止。高橋に相談"],
  [/git\s+reset\s+--hard/, "git reset --hard は禁止。壊したら高橋に"],
  [/git\s+commit\b[^\n]*--amend/, "amend は禁止。新しいコミットを足す"],
  [/rm\s+-rf\s+(\/|~|\.\.)/, "危険な rm"],
];
const BASH_DENY_MEMBER = [
  [/git\s+push\b[^\n]*[\s:]main(\s|$)/, "main への push は高橋だけ。自分のブランチに push"],
  [/pnpm\s+(--filter\s+\S+\s+)?(add|remove|rm|uninstall|i\s+[\w@]|install\s+[\w@])/, "依存の追加・削除は高橋だけ。Slack で頼む"],
  [/\bnpm\s+(i|install)\b(?!\s+-g\s+pnpm)/, "npm install は使わない（pnpm install だけ）"],
  [/git\s+branch\s+-D/, "ブランチの強制削除は禁止"],
  [/(^|[;&|]\s*)(npx\s+|pnpm\s+(dlx\s+|exec\s+)?)?(vercel|railway)\s/, "デプロイは高橋だけ"],
];

const root = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
const mode = process.argv[2] || "--staged";

function fail(msg) {
  process.stderr.write(`\n[となり guard] ${msg}\n\n`);
  process.exit(2);
}

function readRole() {
  const f = resolve(root, ".role.local");
  if (!existsSync(f)) fail("`.role.local` が無い。リポジトリの root で `echo b > .role.local`（b / c / d / takahashi のどれか）を打ってから続ける。");
  const bytes = readFileSync(f);
  const encoding = bytes[0] === 0xff && bytes[1] === 0xfe ? "utf16le" : "utf8";
  const role = bytes.toString(encoding).replace(/^﻿/, "").trim().toLowerCase();
  if (!ROLES.includes(role)) fail(`役割 '${role}' は不明。.role.local は b / c / d / takahashi のどれか。`);
  return role;
}

function checkPaths(role, files) {
  if (role === "takahashi") return;
  const bad = files.map((f) => f.split(sep).join("/")).filter((rel) => TAKAHASHI_ONLY.some((re) => re.test(rel)));
  if (bad.length) fail(`次のファイル（ハーネスと依存）は高橋だけが変える。変えたいことは Slack で高橋に。\n  ${bad.join("\n  ")}`);
}

function git(cmd) {
  return execSync(`git ${cmd}`, { cwd: root, encoding: "utf8" }).trim();
}

function gitSucceeds(cmd) {
  try {
    execSync(`git ${cmd}`, { cwd: root, stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

if (mode === "--staged") {
  const role = readRole();
  const files = git("diff --cached --name-only --no-renames").split("\n").filter(Boolean);
  checkPaths(role, files);
  process.exit(0);
}

if (mode === "--push") {
  const role = readRole();
  const lines = readFileSync(0, "utf8").split("\n").filter(Boolean);
  for (const line of lines) {
    const [localRef, localSha, remoteRef, remoteSha] = line.split(" ");
    if (role !== "takahashi" && /\/main$/.test(remoteRef)) fail("main への push は高橋だけ。自分のブランチ（b/… c/… d/…）に push して PR を出す。");
    if (!/^0+$/.test(remoteSha) && !/^0+$/.test(localSha)) {
      if (!gitSucceeds(`cat-file -e ${remoteSha}`)) fail(`${remoteRef} に手元に無いコミットがある。先に git pull してから push。`);
      if (!gitSucceeds(`merge-base --is-ancestor ${remoteSha} ${localSha}`)) fail(`${remoteRef} への force push は禁止。先に git pull してから push。`);
    }
  }
  process.exit(0);
}

if (mode === "--ci") {
  const author = (process.argv[3] || "").toLowerCase();
  const base = process.argv[4] || "main";
  const team = JSON.parse(readFileSync(resolve(root, "team.json"), "utf8"));
  const role = Object.entries(team).find(([login]) => login.toLowerCase() === author)?.[1];
  if (!role) {
    process.stdout.write(`[となり guard] ${author} は team.json に無いので保護ファイルの検査は省略\n`);
    process.exit(0);
  }
  const files = git(`diff --name-only --no-renames origin/${base}...HEAD`).split("\n").filter(Boolean);
  checkPaths(role, files);
  process.stdout.write(`[となり guard] ${author}（${role}）の変更 ${files.length} 件に保護ファイルは無い\n`);
  process.exit(0);
}

if (mode === "--claude") {
  const input = JSON.parse(readFileSync(0, "utf8"));
  const tool = input.tool_name;
  if (["Edit", "Write", "MultiEdit", "NotebookEdit"].includes(tool)) {
    const role = readRole();
    const raw = input.tool_input?.file_path || input.tool_input?.notebook_path || "";
    const rel = relative(root, resolve(input.cwd || root, raw)).split(sep).join("/");
    if (rel.startsWith("..")) fail(`リポジトリの外（${rel}）は編集しない。`);
    checkPaths(role, [rel]);
  }
  if (tool === "Bash") {
    const role = readRole();
    const cmd = String(input.tool_input?.command || "");
    const rules = role === "takahashi" ? BASH_DENY_ALL : [...BASH_DENY_ALL, ...BASH_DENY_MEMBER];
    for (const [re, msg] of rules) if (re.test(cmd)) fail(`このコマンドは実行しない：${msg}`);
  }
  process.exit(0);
}

fail(`不明なモード ${mode}`);
