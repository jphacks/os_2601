import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, relative, sep } from "node:path";

const ROLES = {
  takahashi: [/^/],
  b: [/^web\/app\/device\//, /^web\/app\/ops\//],
  c: [/^web\/app\/log\//, /^web\/app\/sheets\//, /^worksheets\/ws\d+\.json$/, /^worksheets\/README\.md$/, /^README\.md$/],
  d: [/^web\/app\/page\.tsx$/, /^docs\/pitch\//, /^docs\/video\//],
};

const PROTECTED = [
  /^web\/lib\//, /^api\//, /^openapi\.yaml$/, /^worksheets\/schema\.json$/,
  /^\.github\//, /^\.githooks\//, /^\.claude\//, /^team\.json$/,
  /^package\.json$/, /^web\/package\.json$/, /^pnpm-lock\.yaml$/, /^pnpm-workspace\.yaml$/,
  /^CLAUDE\.md$/, /^AGENTS\.md$/, /^RUNBOOK\.md$/,
];

const BASH_DENY_ALL = [
  [/git\s+push\b[^\n]*(--force\b|\s-f\b|--force-with-lease)/, "force push は禁止。高橋に相談"],
  [/git\s+reset\s+--hard/, "git reset --hard は禁止。壊したら高橋に"],
  [/git\s+commit\b[^\n]*--amend/, "amend は禁止。新しいコミットを足す"],
  [/rm\s+-rf\s+(\/|~|\.\.)/, "危険な rm"],
];
const BASH_DENY_MEMBER = [
  [/git\s+push\b[^\n]*\bmain\b/, "main への push は高橋だけ。自分のブランチに push"],
  [/pnpm\s+(add|remove|rm|i\s+\S|install\s+\S)/, "依存の追加・削除は高橋だけ。Slack で頼む"],
  [/npm\s+(i|install)\b(?!\s+-g\s+pnpm)/, "npm install は使わない（pnpm install だけ）"],
  [/git\s+branch\s+-D/, "ブランチの強制削除は禁止"],
  [/\b(vercel|railway)\s/, "デプロイは高橋だけ"],
];

const root = process.cwd();
const mode = process.argv[2] || "--staged";

function fail(msg) {
  process.stderr.write(`\n[となり guard] ${msg}\n\n`);
  process.exit(2);
}

function readRole() {
  const f = resolve(root, ".role.local");
  if (!existsSync(f)) fail("`.role.local` が無い。リポジトリの root で `echo b > .role.local`（b / c / d / takahashi のどれか）を打ってから続ける。");
  const role = readFileSync(f, "utf8").trim().toLowerCase();
  if (!ROLES[role]) fail(`役割 '${role}' は不明。.role.local は b / c / d / takahashi のどれか。`);
  return role;
}

function checkPaths(role, files) {
  const bad = [];
  for (const f of files) {
    const rel = f.split(sep).join("/");
    if (role !== "takahashi" && PROTECTED.some((re) => re.test(rel))) bad.push(`${rel}（契約・web/lib・api・設定は高橋だけ）`);
    else if (!ROLES[role].some((re) => re.test(rel))) bad.push(`${rel}（役割 '${role}' の担当外）`);
  }
  if (bad.length) fail(`次のファイルは触れない。担当は docs/11_claude_code_guide.md の表。変えたいことは Slack で高橋に。\n  ${bad.join("\n  ")}`);
}

function git(cmd) {
  return execSync(`git ${cmd}`, { cwd: root, encoding: "utf8" }).trim();
}

if (mode === "--staged") {
  const role = readRole();
  const files = git("diff --cached --name-only --diff-filter=ACMRD").split("\n").filter(Boolean);
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
      try {
        execSync(`git merge-base --is-ancestor ${remoteSha} ${localSha}`, { cwd: root, stdio: "ignore" });
      } catch {
        fail(`${remoteRef} への force push は禁止。先に git pull してから push。`);
      }
    }
  }
  process.exit(0);
}

if (mode === "--ci") {
  const actor = (process.argv[3] || "").toLowerCase();
  const base = process.argv[4] || "main";
  const team = JSON.parse(readFileSync(resolve(root, "team.json"), "utf8"));
  const role = Object.entries(team).find(([login]) => login.toLowerCase() === actor)?.[1];
  if (!role) {
    process.stdout.write(`[となり guard] ${actor} は team.json に無いので担当の検査は省略\n`);
    process.exit(0);
  }
  const files = git(`diff --name-only origin/${base}...HEAD`).split("\n").filter(Boolean);
  checkPaths(role, files);
  process.stdout.write(`[となり guard] ${actor}（${role}）の変更 ${files.length} 件は担当内\n`);
  process.exit(0);
}

if (mode === "--claude") {
  const input = JSON.parse(readFileSync(0, "utf8"));
  const cwd = input.cwd || root;
  const tool = input.tool_name;
  if (["Edit", "Write", "MultiEdit", "NotebookEdit"].includes(tool)) {
    const role = readRole();
    const raw = input.tool_input?.file_path || input.tool_input?.notebook_path || "";
    const rel = relative(cwd, resolve(cwd, raw)).split(sep).join("/");
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
