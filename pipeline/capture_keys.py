# -*- coding: utf-8 -*-
"""monitor + v5 capture: poll for Weixin.exe processes, inject validated key-capture JS."""
import frida, time, hashlib, hmac, struct, os, subprocess

LOG_FILE = r"D:\学习\聊天记录\_work\capture.log"
KEY_FILE = r"D:\学习\聊天记录\_work\dbkeys_found.txt"
DB_DIR = r"C:\Users\Lenovo\Documents\xwechat_files\wxid_u08zaj51artd22_1a31\db_storage"

dbs = []
for root, dirs, files in os.walk(DB_DIR):
    for f in files:
        if f.endswith(".db") and not f.endswith(".kvdb"):
            p = os.path.join(root, f)
            try:
                with open(p, "rb") as fh:
                    page1 = fh.read(4096)
                if len(page1) == 4096:
                    dbs.append((os.path.relpath(p, DB_DIR), page1))
            except Exception:
                pass

def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log("loaded %d dbs" % len(dbs))

found = {}
def check_candidate(hexstr):
    try:
        enc = bytes.fromhex(hexstr)
    except Exception:
        return
    if len(enc) != 32:
        return
    for rel, page1 in dbs:
        salt = page1[:16]
        mac_salt = bytes(b ^ 0x3a for b in salt)
        mac_key = hashlib.pbkdf2_hmac("sha512", enc, mac_salt, 2, 32)
        h = hmac.new(mac_key, page1[16:4032], hashlib.sha512)
        h.update(struct.pack("<I", 1))
        if h.digest() == page1[4032:4096] and rel not in found:
            found[rel] = hexstr
            log("*** MATCH: %s = %s" % (rel, hexstr))
            with open(KEY_FILE, "a", encoding="utf-8") as f:
                f.write("%s\t%s\n" % (rel, hexstr))

js = r"""
var CFG_OFF = 0x353bc60;
var MMV1_OFF = 0x7050470;
var seen = {};

function log(s) { send({ type: "log", text: s }); }
function hexStr(p, n) {
    try {
        var u8 = new Uint8Array(p.readByteArray(n));
        var hex = "";
        for (var i = 0; i < u8.length; i++) hex += ("0" + u8[i].toString(16)).slice(-2);
        return hex;
    } catch (e) { return "ERR"; }
}
function offer(label, hexv) {
    if (hexv && hexv.indexOf("ERR") !== 0 && hexv.length === 64 && !seen[hexv]) {
        seen[hexv] = true;
        send({ type: "cand", label: label, hex: hexv });
    }
}
function dumpDesc(label, p) {
    if (!p || p.isNull()) return;
    try {
        var dptr = p.readPointer();
        var len = p.add(8).readU64().toNumber();
        if (len === 32) {
            offer(label, hexStr(dptr, 32));
        } else if (len > 32 && len <= 0x100) {
            var h = hexStr(dptr, len);
            for (var off = 0; off + 32 <= len && off <= 64; off += 8) {
                offer(label, h.substr(off*2, 64));
            }
        }
    } catch (e) {}
}
function setup() {
    var m = Process.getModuleByName("Weixin.dll");
    if (!m) return false;
    var base = m.base;
    Interceptor.attach(base.add(CFG_OFF), {
        onEnter: function(args) {
            if (args[1].toInt32() === 0x20) {
                offer("CFG", hexStr(args[0], 32));
            }
        }
    });
    Interceptor.attach(base.add(MMV1_OFF), {
        onEnter: function(args) {
            dumpDesc("MMV1-r9", args[3]);
            dumpDesc("MMV1-rdx", args[1]);
            dumpDesc("MMV1-r8", args[2]);
        }
    });
    log("hooks installed pid=" + Process.id);
    return true;
}
var tries = 0;
function trySetup() {
    try { if (setup()) return; } catch (e) { log("setup err: " + e); }
    tries++;
    if (tries > 120) { log("GIVEUP pid=" + Process.id); return; }
    setTimeout(trySetup, 1000);
}
trySetup();
"""

device = frida.get_local_device()
hooked = {}
sessions = []

def on_message(msg, data):
    if msg.get("type") == "send":
        payload = msg.get("payload", {})
        if isinstance(payload, dict):
            if payload.get("type") == "log":
                log(payload["text"])
            elif payload.get("type") == "cand":
                check_candidate(payload["hex"])

def hook_pid(pid):
    if pid in hooked:
        return
    try:
        s = device.attach(pid)
        sc = s.create_script(js)
        sc.on("message", on_message)
        sc.load()
        hooked[pid] = sc
        sessions.append(s)
        log("injected pid=%d" % pid)
    except Exception as e:
        log("inject fail pid=%d: %s" % (pid, e))

log("starting Weixin.exe ...")
subprocess.Popen([r"C:\Program Files\Tencent\Weixin\Weixin.exe"])

deadline = time.time() + 900
while time.time() < deadline:
    try:
        for p in device.enumerate_processes():
            if p.name.lower() == "weixin.exe":
                hook_pid(p.pid)
    except Exception as e:
        log("enum err: %s" % e)
    if len(found) >= 5:
        log("enough keys found (%d)" % len(found))
        break
    time.sleep(1)

time.sleep(3)
for sc in hooked.values():
    try: sc.unload()
    except Exception: pass
for s in sessions:
    try: s.detach()
    except Exception: pass
log("DONE found=%d %s" % (len(found), list(found)))
