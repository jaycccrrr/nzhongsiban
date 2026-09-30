# -*- coding: utf-8 -*-
"""Generate full site data JSON for the group-stats website."""
import json, re, datetime, sys, io, os
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import jieba
jieba.setLogLevel(60)

HERE = os.path.dirname(os.path.abspath(__file__))
IN_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'group_msgs.jsonl')
OUT_PATH = os.path.join(HERE, '..', 'content', 'stats.json')

msgs = [json.loads(l) for l in open(IN_PATH, encoding='utf-8')]
def dt(ts): return datetime.datetime.fromtimestamp(ts)
strip = lambda s: (s or '').replace('高2504', '').replace('小小罗', '宋奕萱')
emoji_pat = re.compile(r'\[[^\[\]]{1,8}\]')
for m in msgs:
    m['sender'] = strip(m['sender'])
texts = [m for m in msgs if m['type'] == 1 and m['content'].strip()]

senders = [s for s, _ in Counter(m['sender'] for m in msgs if m['sender']).most_common()]
days_all = sorted(set(dt(m['ts']).strftime('%Y-%m-%d') for m in msgs))
day_idx = {d: i for i, d in enumerate(days_all)}

stop = set('的 了 是 我 你 他 她 它 们 也 都 就 还 在 和 吗 吧 啊 呢 嘛 哦 嗯 不 没 有 个 这 那 啥 说 去 来 到 得 着 过 要 会 能 可以 就是 不是 什么 怎么 这样 那个 一个 我们 你们 他们 真的 还是 但是 因为 所以 如果 现在 知道 没有 这么 为什么 自己 已经 一下 一点 一直 不会 不要 让 把 被 跟 从 给 而且 或者 的话 时候 东西 问题 意思 可能 应该 觉得 这个 还有 然后 直接 今天 明天 昨天 感觉 好像 出来 不能 有点 其实 一样 那么 这种 那种 怎样 大家 兄弟 哥们 哈哈 哈哈哈 笑死 可以 还是 没有 不要'.split())

food_kws = ['吃', '饭', '火锅', '烧烤', '奶茶', '外卖', '食堂', '美食', '烤', '面', '菜', '餐厅', '麦当劳', '肯德基', '饿']
game_kws = ['王者', '游戏', '开黑', '五排', '排位', '上分', '吃鸡', '原神', '金铲铲']

# ---------- per-person accumulation ----------
P = {s: dict(name=s, msgs=0, chars=0, textMsgs=0, stickers=0, images=0, voices=0, videos=0,
             questions=0, haha=0, food=0, game=0, night=0, early=0, recalls=0,
             hours=[0]*24, days=set(), perDay=Counter(), words=Counter(), emojis=Counter(),
             maxCombo=0, lens=[]) for s in senders}

# combo tracking
prev_s, combo = None, 0
for m in msgs:
    s = m['sender']
    if not s or s not in P:
        prev_s, combo = None, 0
        continue
    p = P[s]
    p['msgs'] += 1
    d = dt(m['ts'])
    p['hours'][d.hour] += 1
    p['days'].add(d.strftime('%Y-%m-%d'))
    p['perDay'][d.strftime('%Y-%m-%d')] += 1
    if 0 <= d.hour < 6: p['night'] += 1
    if 5 <= d.hour < 8: p['early'] += 1
    if m['type'] == 47: p['stickers'] += 1
    elif m['type'] == 3: p['images'] += 1
    elif m['type'] == 34: p['voices'] += 1
    elif m['type'] == 43: p['videos'] += 1
    elif m['type'] == 1:
        c = m['content']
        p['textMsgs'] += 1
        p['chars'] += len(c)
        p['lens'].append(len(c))
        if '？' in c or '?' in c: p['questions'] += 1
        if '哈哈' in c: p['haha'] += 1
        if any(k in c for k in food_kws): p['food'] += 1
        if any(k in c for k in game_kws): p['game'] += 1
        for e in re.findall(r'\[([^\[\]]{1,8})\]', c):
            p['emojis'][e] += 1
        for w in jieba.cut(emoji_pat.sub(' ', c)):
            w = w.strip()
            if len(w) >= 2 and w not in stop and not re.match(r'^[\d\W]+$', w):
                p['words'][w] += 1
    # combo
    if s == prev_s:
        combo += 1
    else:
        combo = 1
    prev_s = s
    if combo > p['maxCombo']:
        p['maxCombo'] = combo

# recalls
for m in msgs:
    if m['type'] == 10000 and '撤回' in m['content']:
        mm = re.search(r'<content>"([^"<]+)"\s*撤回了一条消息</content>', m['content']) or re.search(r'"([^"<]+)"\s*撤回了一条消息', m['content'])
        if mm:
            name = strip(mm.group(1))
            if name in P: P[name]['recalls'] += 1

# ---------- atmosphere & QA ----------
after = defaultdict(list)
for i, m in enumerate(msgs):
    s = m['sender']
    if not s or s not in P: continue
    cnt, j = 0, i + 1
    while j < len(msgs) and msgs[j]['ts'] - m['ts'] <= 600:
        if msgs[j]['sender'] != s: cnt += 1
        j += 1
    after[s].append(cnt)
qa = Counter()
for i in range(1, len(msgs)):
    prev, cur = msgs[i-1], msgs[i]
    if prev['type'] == 1 and ('？' in prev['content'] or '?' in prev['content']) \
       and cur['sender'] and cur['sender'] != prev['sender'] and cur['ts'] - prev['ts'] <= 300:
        qa[cur['sender']] += 1

# ---------- pairs (directed reply stats) ----------
pair_cnt = Counter()       # sorted tuple -> count of <60s exchanges
pair_dir = defaultdict(Counter)  # (a,b) directed: b replies to a
pair_time = defaultdict(list)
for i in range(1, len(msgs)):
    a, b = msgs[i-1]['sender'], msgs[i]['sender']
    if not a or not b or a == b or a not in P or b not in P: continue
    gap = msgs[i]['ts'] - msgs[i-1]['ts']
    if gap < 60:
        pair_cnt[tuple(sorted((a, b)))] += 1
        pair_dir[tuple(sorted((a, b)))][b] += 1
        pair_time[tuple(sorted((a, b)))].append(gap)

pairs = []
for (a, b), c in pair_cnt.most_common():
    times = pair_time[(a, b)]
    pairs.append(dict(a=a, b=b, count=c,
                      avgSec=round(sum(times)/len(times), 1),
                      dirA=pair_dir[(a, b)].get(a, 0),  # a 接 b 的话次数
                      dirB=pair_dir[(a, b)].get(b, 0)))

# ---------- finalize persons ----------
persons = []
for s in senders:
    p = P[s]
    days_list = sorted(day_idx[d] for d in p['days'])
    max_gap = max((days_list[i+1]-days_list[i] for i in range(len(days_list)-1)), default=0)
    lens = sorted(p['lens'])
    median_len = lens[len(lens)//2] if lens else 0
    best_day, best_cnt = p['perDay'].most_common(1)[0] if p['perDay'] else ('', 0)
    peak_hour = max(range(24), key=lambda h: p['hours'][h])
    persons.append(dict(
        name=s, msgs=p['msgs'], chars=p['chars'], textMsgs=p['textMsgs'],
        avgLen=round(p['chars']/max(p['textMsgs'],1), 1), medianLen=median_len,
        stickers=p['stickers'], images=p['images'], voices=p['voices'], videos=p['videos'],
        questions=p['questions'], haha=p['haha'], food=p['food'], game=p['game'],
        night=p['night'], early=p['early'], recalls=p['recalls'],
        activeDays=len(p['days']), maxDive=max_gap, peakHour=peak_hour,
        hours=p['hours'], maxCombo=p['maxCombo'],
        bestDay=best_day, bestDayCount=best_cnt,
        atmosphere=round(sum(after[s])/max(len(after[s]),1), 2),
        qa=qa.get(s, 0),
        catchphrases=[w for w, c in p['words'].most_common(6)],
        topEmojis=[e for e, c in p['emojis'].most_common(4)],
    ))

# ---------- overview ----------
day_cnt = Counter(dt(m['ts']).strftime('%Y-%m-%d') for m in msgs)
mon_cnt = Counter(dt(m['ts']).strftime('%Y-%m') for m in msgs)
hour_cnt = [0]*24
for m in msgs: hour_cnt[dt(m['ts']).hour] += 1
face_cnt = Counter()
for m in texts:
    for e in re.findall(r'\[([^\[\]]{1,8})\]', m['content']):
        face_cnt[e] += 1
wc = Counter()
for m in texts:
    for w in jieba.cut(emoji_pat.sub(' ', m['content'])):
        w = w.strip()
        if len(w) >= 2 and w not in stop and not re.match(r'^[\d\W]+$', w):
            wc[w] += 1
kws = ['哈哈', '笑死', '牛逼', '666', '收到', '谢谢', '晚安', '考试', '作业', '老师', '高考', '大学', '王者', '睡觉', '吃了']
alltext = '\n'.join(m['content'] for m in texts)
renames = [dict(date=dt(m['ts']).strftime('%Y-%m-%d'), text=m['content'][:60])
           for m in msgs if m['type'] == 10000 and '修改群名' in m['content']]

# silence (topic killer)
silence = Counter()
for i in range(1, len(msgs)):
    if msgs[i]['ts'] - msgs[i-1]['ts'] >= 7200 and msgs[i-1]['sender'] != msgs[i]['sender'] and msgs[i-1]['sender'] in P:
        silence[msgs[i-1]['sender']] += 1

data = dict(
    meta=dict(start=dt(msgs[0]['ts']).strftime('%Y-%m-%d'), end=dt(msgs[-1]['ts']).strftime('%Y-%m-%d'),
              total=len(msgs), days=(dt(msgs[-1]['ts'])-dt(msgs[0]['ts'])).days+1,
              textTotal=len(texts), charTotal=sum(len(m['content']) for m in texts),
              members=len(senders)),
    types=dict(text=len(texts), sticker=sum(1 for m in msgs if m['type']==47),
               image=sum(1 for m in msgs if m['type']==3), voice=sum(1 for m in msgs if m['type']==34),
               video=sum(1 for m in msgs if m['type']==43)),
    months=[[m, mon_cnt[m]] for m in sorted(mon_cnt)],
    hours=hour_cnt,
    topDays=[[d, c] for d, c in day_cnt.most_common(10)],
    emojis=[[e, c] for e, c in face_cnt.most_common(10)],
    words=[[w, c] for w, c in wc.most_common(30)],
    keywords=[[k, alltext.count(k)] for k in kws],
    renames=renames,
    silenceKings=[[s, c] for s, c in silence.most_common(5)],
    persons=persons,
    pairs=pairs,
)

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
print('written ->', os.path.abspath(OUT_PATH))
print('OK  persons=%d pairs=%d size=%.1fKB' % (len(persons), len(pairs), len(json.dumps(data, ensure_ascii=False))/1024))
for p in persons:
    print(p['name'], p['msgs'], '条 | 口头禅:', '、'.join(p['catchphrases'][:3]), '| 表情:', ' '.join('[%s]'%e for e in p['topEmojis'][:3]))
