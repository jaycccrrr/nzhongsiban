# -*- coding: utf-8 -*-
"""Export group messages to JSONL with decompression and sender-prefix stripping."""
import sqlite3, hashlib, json, re, sys, io
import zstandard
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

GROUP = '49099912496@chatroom'

mcon = sqlite3.connect('plain/message_0.db')
ccon = sqlite3.connect('plain/contact.db')

id2user = dict(mcon.execute('SELECT rowid, user_name FROM Name2Id').fetchall())
names = {}
for u, nick, remark in ccon.execute('SELECT username, nick_name, remark FROM contact'):
    names[u] = remark or nick or u

def disp(rsid):
    u = id2user.get(rsid, str(rsid))
    return names.get(u, u)

d = zstandard.ZstdDecompressor()
prefix_re = re.compile(r'^(wxid_\w+|\w+@chatroom):\n?')

def clean(content, compressed):
    if content is None:
        return ''
    if compressed == 4 and isinstance(content, bytes):
        try:
            content = d.decompress(content, max_output_size=16 * 1024 * 1024)
        except Exception:
            return ''
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8', errors='replace')
        except Exception:
            return ''
    return prefix_re.sub('', content)

t = 'Msg_' + hashlib.md5(GROUP.encode()).hexdigest()
n = 0
with open('group_msgs.jsonl', 'w', encoding='utf-8') as f:
    for rsid, ctime, ltype, content, comp in mcon.execute(
        'SELECT real_sender_id, create_time, local_type, message_content, WCDB_CT_message_content FROM "%s" ORDER BY create_time' % t):
        f.write(json.dumps({'ts': ctime, 'sender': disp(rsid), 'type': ltype,
                            'content': clean(content, comp)}, ensure_ascii=False) + '\n')
        n += 1
print('exported', n)
