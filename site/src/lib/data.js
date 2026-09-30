// 数据读取与文案生成（构建时在 Node 环境运行）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const C = p => path.join(ROOT, 'content', p);

export const stats = JSON.parse(fs.readFileSync(C('stats.json'), 'utf-8'));
export const members = JSON.parse(fs.readFileSync(C('members.json'), 'utf-8'));

/* ---------- 工具 ---------- */
export const fmt = n => Number(n).toLocaleString('en-US');
export const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const COLORS = ['#c96f4a','#8a9a5b','#d9a441','#7a8fa6','#b56576','#6d8ea0','#a1887f','#c08457','#94868c','#5f8d7a','#b08968','#9b7eb8'];
export const pcolor = i => COLORS[i % COLORS.length];

/* ---------- 极简 markdown（段落/加粗/图片/列表） ---------- */
export function md(src, base) {
  const inline = s => esc(s)
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, a, u2) => `<img src="${u2.startsWith('http') ? u2 : base + u2.replace(/^\//, '')}" alt="${a}" loading="lazy">`)
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const blocks = src.split(/\n{2,}/).map(b => b.trim()).filter(Boolean);
  return blocks.map(b => {
    if (/^- /.test(b)) return '<ul>' + b.split('\n').map(l => `<li>${inline(l.replace(/^- /, ''))}</li>`).join('') + '</ul>';
    return `<p>${inline(b).replace(/\n/g, '<br>')}</p>`;
  }).join('');
}

export function loadMdDir(dir) {
  const abs = C(dir);
  if (!fs.existsSync(abs)) return [];
  return fs.readdirSync(abs).filter(f => f.endsWith('.md')).map(f => {
    const raw = fs.readFileSync(path.join(abs, f), 'utf-8');
    const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(raw);
    const fm = {};
    if (m) for (const line of m[1].split(/\r?\n/)) {
      const i = line.indexOf(':');
      if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim();
    }
    return { slug: f.replace(/\.md$/, ''), ...fm, body: (m ? m[2] : raw).trim() };
  }).sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
}

export function listPhotos() {
  const abs = C('photos');
  const out = [];
  const walk = (d, rel) => {
    if (!fs.existsSync(d)) return;
    for (const f of fs.readdirSync(d, { withFileTypes: true })) {
      const r = rel ? rel + '/' + f.name : f.name;
      if (f.isDirectory()) walk(path.join(d, f.name), r);
      else if (/\.(jpe?g|png|webp|gif)$/i.test(f.name)) out.push(r);
    }
  };
  walk(abs, '');
  return out.filter(r => !r.startsWith('avatars/'));
}

/* ---------- 人设标签（数据驱动） ---------- */
export function deriveTags(D) {
  const ps = D.persons, T = {};
  ps.forEach(p => T[p.name] = []);
  const topBy = fn => ps.reduce((b, p) => (!b || fn(p) > fn(b)) ? p : b, null);
  const add = (p, t) => { if (T[p.name].length < 3 && !T[p.name].includes(t)) T[p.name].push(t); };
  add(topBy(p => p.msgs), '群里的话痨');
  add(topBy(p => p.atmosphere), '气氛组组长');
  add(topBy(p => p.qa), '有问必答');
  add(topBy(p => p.food), '美食雷达');
  add(topBy(p => p.haha), '快乐源泉');
  const g = topBy(p => p.game); if (g.game > 20) add(g, '电竞选手');
  add(topBy(p => p.night), '深夜守夜人');
  add(topBy(p => p.early), '早起第一人');
  add(topBy(p => p.stickers / Math.max(p.textMsgs, 1)), '表情包富翁');
  add(topBy(p => p.recalls), '欲言又止');
  add(topBy(p => p.maxDive), '神出鬼没');
  if (D.silenceKings.length) { const sk = ps.find(p => p.name === D.silenceKings[0][0]); if (sk) add(sk, '话题终结者'); }
  for (const p of ps) {
    if (p.night / Math.max(p.msgs, 1) > 0.06) add(p, '夜猫子');
    if (p.activeDays / D.meta.days > 0.55) add(p, '全勤标兵');
    if (!T[p.name].length) T[p.name].push('安静的观察家');
  }
  return T;
}

/* ---------- 人物速写（情感化叙述） ---------- */
export function personStory(p, D) {
  const s = [];
  const perDay = (p.msgs / D.meta.days).toFixed(1);
  s.push(`这一年，${p.name}在群里说了 ${fmt(p.msgs)} 句话，平均一天 ${perDay} 句。`);
  if (p.activeDays / D.meta.days > 0.55) s.push(`${D.meta.days} 天里有 ${p.activeDays} 天都能见到 TA，几乎从未缺席。`);
  else if (p.maxDive >= 14) s.push(`TA 有过长达 ${p.maxDive} 天的沉默，但总会回来。`);
  const nightPct = Math.round(p.night / Math.max(p.msgs, 1) * 100);
  if (nightPct > 6) s.push(`TA 有 ${nightPct}% 的话是在凌晨说的——那些睡不着的夜晚，群里还有 TA。`);
  else if (p.early > 100) s.push(`清晨 5 到 8 点，TA 已经说了 ${p.early} 句话，比很多人的闹钟都准时。`);
  else s.push(`TA 最常在 ${p.peakHour} 点出现。`);
  if (p.qa > 100) s.push(`别人抛出问题，TA 有 ${p.qa} 次在 5 分钟内赶到——靠谱的代名词。`);
  if (p.recalls > 50) s.push(`TA 撤回了 ${p.recalls} 条消息，那些欲言又止的瞬间，只有 TA 自己知道。`);
  if (p.topEmojis.length) s.push(`TA 的情绪藏在 ${p.topEmojis.slice(0, 3).map(e => `[${e}]`).join(' ')} 里。`);
  if (p.catchphrases.length) s.push(`如果只听三个字就认出 TA，那一定是「${p.catchphrases[0]}」。`);
  return s.join('');
}

/* ---------- 关系叙述 ---------- */
export function pairStory(x) {
  const faster = x.dirA >= x.dirB ? [x.a, x.b] : [x.b, x.a];
  return `${faster[1]}一开口，${faster[0]}平均 ${Math.round(x.avgSec)} 秒内就会出现——这一年，这样的默契发生了 ${fmt(x.count)} 次。`;
}

/* ---------- 总览精选叙述 ---------- */
export function overviewStory(D) {
  const M = D.meta, s = [];
  const late = D.hours.slice(0, 6).reduce((a, b) => a + b, 0);
  s.push(`${M.start} 到 ${M.end}，${M.days} 天，${M.members} 个人，${fmt(M.total)} 条消息。`);
  s.push(`其中 ${fmt(late)} 条，是在凌晨 0 点到 6 点说的——那些本该睡觉的时刻，我们选择和彼此说话。`);
  const [bd, bc] = D.topDays[0];
  s.push(`最热闹的一天是 ${bd}，${fmt(bc)} 条消息，平均一分钟就有 ${(bc / 1440 * 24).toFixed(0)} 条。`);
  return s;
}
