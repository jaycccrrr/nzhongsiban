// 把 content/photos 同步到 site/public/photos（构建前自动执行）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, 'content', 'photos');
const DST = path.join(ROOT, 'site', 'public', 'photos');

fs.rmSync(DST, { recursive: true, force: true });

let count = 0;
function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) copyDir(s, d);
    else { fs.copyFileSync(s, d); count++; }
  }
}
if (fs.existsSync(SRC)) {
  copyDir(SRC, DST);
  console.log(`[sync-photos] copied ${count} file(s)`);
} else {
  fs.mkdirSync(DST, { recursive: true });
  console.log('[sync-photos] no photos yet');
}
