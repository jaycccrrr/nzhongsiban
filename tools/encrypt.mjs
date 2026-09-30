// 整站加密门禁：构建后对 dist 加密
// 用法：SITE_PASSWORD=xxx node tools/encrypt.mjs   或在 tools/password.txt 写入密码
// - 所有 .html 页面 → 替换为密码门禁页（内含密文，输入正确密码后本地解密还原）
// - photos/ 下的图片 → 加密为 .enc（页面内 JS 自动解密显示）
// - CSS/JS 资源不含隐私内容，保持明文
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { webcrypto, randomBytes } from 'node:crypto';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'site', 'dist');
const subtle = webcrypto.subtle;

let password = process.env.SITE_PASSWORD;
const pwFile = path.join(ROOT, 'tools', 'password.txt');
if (!password && fs.existsSync(pwFile)) password = fs.readFileSync(pwFile, 'utf-8').trim();
if (!password) {
  console.log('[encrypt] 未设置密码（SITE_PASSWORD 或 tools/password.txt），跳过加密，站点为明文。');
  process.exit(0);
}

const enc = new TextEncoder();
async function encryptBytes(data) {
  const salt = randomBytes(16), iv = randomBytes(12);
  const keyMaterial = await subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  const key = await subtle.deriveKey({ name: 'PBKDF2', salt, iterations: 150000, hash: 'SHA-256' }, keyMaterial, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
  const ct = new Uint8Array(await subtle.encrypt({ name: 'AES-GCM', iv }, key, data));
  const out = new Uint8Array(28 + ct.length);
  out.set(salt, 0); out.set(iv, 16); out.set(ct, 28);
  return Buffer.from(out).toString('base64');
}

// 门禁页模板（注入密文）
const shell = payload => `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>廿中四班</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#faf6ee;font-family:"PingFang SC","Microsoft YaHei",sans-serif}
.box{text-align:center;padding:40px 24px;max-width:340px}
h1{font-family:"Noto Serif SC","Songti SC",serif;letter-spacing:8px;color:#3d362e;font-size:32px;margin:0 0 8px}
.sub{color:#8a7f6d;font-size:13px;margin-bottom:28px}
input{width:100%;padding:13px 16px;border:1.5px solid #e8ddc9;border-radius:12px;font-size:16px;text-align:center;letter-spacing:2px;outline:none;background:#fffdf8;color:#3d362e;box-sizing:border-box}
input:focus{border-color:#c96f4a}
button{margin-top:14px;width:100%;padding:13px;border:none;border-radius:12px;background:#c96f4a;color:#fff;font-size:15px;letter-spacing:4px;cursor:pointer}
button:active{opacity:.85}
.err{color:#b56576;font-size:13px;margin-top:12px;display:none}
</style></head><body>
<div class="box"><h1>廿中四班</h1><div class="sub">这是我们的小天地，输入密码进入</div>
<form id="f"><input id="pw" type="password" autocomplete="current-password" placeholder="密码" autofocus>
<button type="submit">进 入</button><div class="err" id="err">密码不对，再想想？</div></form></div>
<script>
var P="${payload}";
function b2b(b){var s=atob(b),a=new Uint8Array(s.length);for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a}
function hex(a){return Array.from(a).map(function(x){return x.toString(16).padStart(2,'0')}).join('')}
function unhex(h){var a=new Uint8Array(h.length/2);for(var i=0;i<a.length;i++)a[i]=parseInt(h.substr(i*2,2),16);return a}
async function dec(keyBytes){
  var raw=b2b(P),salt=raw.slice(0,16),iv=raw.slice(16,28),ct=raw.slice(28);
  var key=await crypto.subtle.importKey('raw',keyBytes,'AES-GCM',false,['decrypt']);
  var pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:iv},key,ct);
  return new TextDecoder().decode(pt);
}
async function derive(pw,salt){
  var km=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);
  var k=await crypto.subtle.deriveKey({name:'PBKDF2',salt:salt,iterations:150000,hash:'SHA-256'},km,{name:'AES-GCM',length:256},true,['encrypt']);
  return new Uint8Array(await crypto.subtle.exportKey('raw',k));
}
function show(html){document.open();document.write(html);document.close();}
async function tryKey(kb){try{var h=await dec(kb);sessionStorage.setItem('gk',hex(kb));show(h);}catch(e){document.getElementById('err').style.display='block';}}
(function(){var gk=sessionStorage.getItem('gk');if(gk)tryKey(unhex(gk));})();
document.getElementById('f').onsubmit=async function(e){
  e.preventDefault();
  var pw=document.getElementById('pw').value;if(!pw)return;
  var salt=b2b(P).slice(0,16);
  tryKey(await derive(pw,salt));
};
<\/script></body></html>`;

function walk(dir, fn) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, fn); else fn(p);
  }
}

let htmlCount = 0, photoCount = 0;
const jobs = [];
walk(DIST, p => {
  const rel = path.relative(DIST, p).replace(/\\/g, '/');
  if (/\.html?$/i.test(p)) {
    jobs.push((async () => {
      const payload = await encryptBytes(fs.readFileSync(p));
      fs.writeFileSync(p, shell(payload));
      htmlCount++;
    })());
  } else if (/^photos\//.test(rel) && /\.(jpe?g|png|webp|gif)$/i.test(p)) {
    jobs.push((async () => {
      const payload = await encryptBytes(fs.readFileSync(p));
      fs.writeFileSync(p + '.enc', payload);
      fs.unlinkSync(p);
      photoCount++;
    })());
  }
});
await Promise.all(jobs);
console.log(`[encrypt] 完成：${htmlCount} 个页面 + ${photoCount} 张照片已加密`);
