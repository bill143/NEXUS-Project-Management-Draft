#!/usr/bin/env node
// One-shot read-only audit of emails + URLs across the repo.
// Writes EMAIL_URL_AUDIT.md at repo root. Modifies nothing else.

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.argv[2] ?? process.cwd());
const REPORT_PATH = path.join(ROOT, 'EMAIL_URL_AUDIT.md');

const EXCLUDED_DIRS = new Set([
  'node_modules', '.next', '.git', 'dist', 'build', '.turbo', '.vercel',
  'coverage', '.venv', 'venv', '__pycache__', '.pytest_cache', 'htmlcov',
  '.idea', '.vscode', 'pg_data', 'minio_data', 'qdrant_data', '.eggs',
]);

const BINARY_EXT = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.ico',
  '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.pdf', '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
  '.exe', '.dll', '.so', '.dylib', '.bin',
  '.mp3', '.mp4', '.wav', '.ogg', '.webm', '.mov', '.avi',
  '.parquet', '.lance', '.db', '.sqlite', '.sqlite3',
  '.whl', '.pyc',
]);

const SKIP_FILE_NAMES = new Set([
  'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'Cargo.lock',
  'poetry.lock', 'uv.lock', 'composer.lock', 'Gemfile.lock',
]);

const SKIP_FILE_REGEX = [
  /\.lock$/i,
  /\.log$/i,
  /\.log\.(err|out)$/i,
  /\.db-(shm|wal|journal)$/i,
  /\.tar\.gz$/i,
  /\.tsbuildinfo$/i,
];

const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+\b/g;
const URL_RE = /https?:\/\/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+/g;

const TRAILING_TRIM_RE = /[)>\]\}'",.;:!?]+$/;

const COMMENT_PATTERNS = [
  { ext: ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.go', '.java', '.kt', '.swift', '.rs', '.c', '.cpp', '.h', '.hpp'], re: /^\s*\/\// },
  { ext: ['.py', '.sh', '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg', '.env', '.env.example', '.dockerignore', '.gitignore'], re: /^\s*#/ },
  { ext: ['.sql'], re: /^\s*--/ },
  { ext: ['.lua'], re: /^\s*--/ },
  { ext: ['.html', '.xml', '.svg', '.vue'], re: /<!--/ },
  { ext: ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.go', '.java', '.kt', '.swift', '.rs', '.c', '.cpp', '.h', '.hpp'], re: /^\s*(\/\*|\*\s)/ },
];

function isBinaryByExt(filename) {
  const ext = path.extname(filename).toLowerCase();
  return BINARY_EXT.has(ext);
}

function shouldSkipFile(filename) {
  if (SKIP_FILE_NAMES.has(filename)) return true;
  for (const re of SKIP_FILE_REGEX) if (re.test(filename)) return true;
  return false;
}

function looksBinary(buf) {
  const slice = buf.subarray(0, Math.min(buf.length, 4096));
  for (let i = 0; i < slice.length; i++) {
    if (slice[i] === 0) return true;
  }
  return false;
}

function isInComment(line, ext) {
  for (const p of COMMENT_PATTERNS) {
    if (p.ext.includes(ext) && p.re.test(line)) return true;
  }
  return false;
}

function isEnvOrSecretFile(absPath) {
  const base = path.basename(absPath).toLowerCase();
  if (base.startsWith('.env')) return true;
  if (base.includes('secret')) return true;
  if (base === 'credentials' || base === 'credentials.json') return true;
  return false;
}

function classifyContext(line, ext, absPath) {
  if (isEnvOrSecretFile(absPath)) return '[ENV/SECRET]';
  if (isInComment(line, ext)) return '[COMMENT]';
  return '';
}

function tryReadText(absPath) {
  try {
    const buf = fs.readFileSync(absPath);
    if (looksBinary(buf)) return null;
    return buf.toString('utf8');
  } catch {
    return null;
  }
}

function* walk(dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) {
      if (EXCLUDED_DIRS.has(entry.name)) continue;
      yield* walk(full);
    } else if (entry.isFile()) {
      if (isBinaryByExt(entry.name)) continue;
      if (shouldSkipFile(entry.name)) continue;
      yield full;
    }
  }
}

function trimTrailing(s) {
  let prev;
  do {
    prev = s;
    s = s.replace(TRAILING_TRIM_RE, '');
  } while (s !== prev);
  return s;
}

function registeredDomain(host) {
  const parts = host.toLowerCase().split('.').filter(Boolean);
  if (parts.length <= 2) return parts.join('.');
  const twoLevelTlds = new Set(['co.uk', 'co.jp', 'com.au', 'com.br', 'com.cn', 'co.in']);
  const last2 = parts.slice(-2).join('.');
  if (twoLevelTlds.has(last2) && parts.length >= 3) {
    return parts.slice(-3).join('.');
  }
  return last2;
}

function safeHost(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return '';
  }
}

const emailRows = [];
const urlRows = [];
const filesScanned = new Set();
const filesWithMatches = new Set();

const startedAt = new Date();

for (const file of walk(ROOT)) {
  filesScanned.add(file);
  const text = tryReadText(file);
  if (text === null) continue;
  const ext = path.extname(file).toLowerCase();
  const lines = text.split(/\r?\n/);
  const rel = path.relative(ROOT, file).replace(/\\/g, '/');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    const emails = line.match(EMAIL_RE);
    if (emails) {
      const seen = new Set();
      for (const raw of emails) {
        const email = trimTrailing(raw);
        if (!email || seen.has(email)) continue;
        seen.add(email);
        const ctx = classifyContext(line, ext, file);
        emailRows.push({
          email,
          file: rel,
          line: i + 1,
          ctx: (ctx ? ctx + ' ' : '') + line.trim().slice(0, 200),
        });
        filesWithMatches.add(file);
      }
    }

    const urls = line.match(URL_RE);
    if (urls) {
      const seen = new Set();
      for (const raw of urls) {
        const url = trimTrailing(raw);
        if (!url || seen.has(url)) continue;
        seen.add(url);
        const ctx = classifyContext(line, ext, file);
        urlRows.push({
          url,
          file: rel,
          line: i + 1,
          ctx: (ctx ? ctx + ' ' : '') + line.trim().slice(0, 200),
        });
        filesWithMatches.add(file);
      }
    }
  }
}

emailRows.sort((a, b) => a.email.localeCompare(b.email) || a.file.localeCompare(b.file) || a.line - b.line);
urlRows.sort((a, b) => a.url.localeCompare(b.url) || a.file.localeCompare(b.file) || a.line - b.line);

const uniqueEmails = [...new Set(emailRows.map(r => r.email))].sort();
const uniqueUrls = [...new Set(urlRows.map(r => r.url))].sort();

const urlsByDomain = new Map();
for (const u of uniqueUrls) {
  const host = safeHost(u);
  if (!host) continue;
  const dom = registeredDomain(host);
  if (!urlsByDomain.has(dom)) urlsByDomain.set(dom, []);
  urlsByDomain.get(dom).push(u);
}

function escMd(s) {
  return s.replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

let out = '';
out += `# Email & URL Audit Report\n\n`;
out += `Generated: ${startedAt.toISOString()}\n`;
out += `Repo root: ${ROOT.replace(/\\/g, '/')}\n\n`;
out += `## 1. Email Addresses\n\n`;
out += `| Email | File Path | Line # | Context |\n`;
out += `|---|---|---|---|\n`;
for (const r of emailRows) {
  out += `| ${escMd(r.email)} | ${escMd(r.file)} | ${r.line} | ${escMd(r.ctx)} |\n`;
}
out += `\n## 2. Web URLs\n\n`;
out += `| URL | File Path | Line # | Context |\n`;
out += `|---|---|---|---|\n`;
for (const r of urlRows) {
  out += `| ${escMd(r.url)} | ${escMd(r.file)} | ${r.line} | ${escMd(r.ctx)} |\n`;
}
out += `\n## 3. Summary\n\n`;
out += `- Total unique emails: **${uniqueEmails.length}**\n`;
out += `- Total unique URLs: **${uniqueUrls.length}**\n`;
out += `- Files scanned: **${filesScanned.size}**\n`;
out += `- Files with matches: **${filesWithMatches.size}**\n`;
out += `- Total email occurrences: **${emailRows.length}**\n`;
out += `- Total URL occurrences: **${urlRows.length}**\n`;
out += `\n## 4. Unique Email Addresses (deduped)\n\n`;
for (const e of uniqueEmails) out += `- ${e}\n`;
out += `\n## 5. Unique URLs (deduped, grouped by registered domain)\n\n`;
const sortedDomains = [...urlsByDomain.keys()].sort();
for (const dom of sortedDomains) {
  const list = urlsByDomain.get(dom).slice().sort();
  out += `### ${dom} (${list.length})\n\n`;
  for (const u of list) out += `- ${u}\n`;
  out += `\n`;
}

fs.writeFileSync(REPORT_PATH, out, 'utf8');
console.log(`Wrote ${REPORT_PATH}`);
console.log(`emails=${emailRows.length} urls=${urlRows.length} files=${filesScanned.size} hits=${filesWithMatches.size}`);
