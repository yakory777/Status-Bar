#!/usr/bin/env python3
"""
Экран задачи: статус, план из сегментов, счётчик, время — 536×240.

    python tools/render_task.py --theme claude    # → docs/claude_task.gif
    python tools/render_task.py --theme codex     # → docs/codex_task.gif
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts') + os.sep
DOCS = os.path.join(os.path.dirname(HERE), 'docs')

THEMES = {
    'claude': dict(
        text=(255, 255, 255), gray=(0x8E, 0x8E, 0x93), empty=(0x1C, 0x1C, 0x1E),
        fonts=('DejaVuSans.ttf', 18, 'DejaVuSans-Bold.ttf', 27, 'DejaVuSans-Bold.ttf', 40),
        states={'idle': (0x8E, 0x8E, 0x93), 'start': (0xFF, 0x45, 0x3A), 'work': (0xFF, 0x9F, 0x0A),
                'wait': (0xFF, 0xD6, 0x0A), 'done': (0x30, 0xD1, 0x58)},
        title='Отрефактори модуль авторизации',
        steps=['Изучаю структуру проекта', 'Правлю модуль авторизации', 'Обновляю логику токенов',
               'Пишу тесты', 'Запускаю тесты'],
        ask='Разрешить запуск npm test?',
    ),
    'codex': dict(
        text=(0xEC, 0xEC, 0xF1), gray=(0x8E, 0x8E, 0xA0), empty=(0x26, 0x27, 0x2E),
        fonts=('DejaVuSansMono.ttf', 17, 'DejaVuSansMono-Bold.ttf', 25, 'DejaVuSansMono-Bold.ttf', 40),
        states={'idle': (0x8E, 0x8E, 0xA0), 'start': (0xEC, 0xEC, 0xF1), 'work': (0x10, 0xA3, 0x7F),
                'wait': (0xF5, 0xA5, 0x24), 'done': (0x6E, 0xE7, 0xB7)},
        title='Почини падающие тесты',
        steps=['Ищу падающий тест', 'Читаю стектрейс', 'Правлю парсер дат', 'Запускаю pytest', 'Проверяю покрытие'],
        ask='Разрешить запуск pytest?',
    ),
}
LABELS = {'idle': 'Ожидание', 'start': 'Старт', 'work': 'В работе', 'wait': 'Ждёт вас', 'done': 'Готово'}

ap = argparse.ArgumentParser()
ap.add_argument('--theme', choices=sorted(THEMES), default='claude')
ap.add_argument('--out')
ARGS = ap.parse_args()
TH = THEMES[ARGS.theme]

W, H, M, BAR_Y, BAR_H, GAP, MAX_SEG = 536, 240, 20, 146, 14, 8, 12
K = 3                      # суперсэмплинг
C_TEXT, C_GRAY, C_EMPTY = TH['text'], TH['gray'], TH['empty']
_fs = TH['fonts']
f_small = ImageFont.truetype(FD + _fs[0], _fs[1] * K)
f_title = ImageFont.truetype(FD + _fs[2], _fs[3] * K)
f_big = ImageFont.truetype(FD + _fs[4], _fs[5] * K)
STATES = {k: (v, LABELS[k]) for k, v in TH['states'].items()}
active_st = lambda s: s in ('start', 'work', 'wait')

def bez(x1,y1,x2,y2):
    def f(t):
        lo,hi,u=0.0,1.0,t
        for _ in range(20):
            u=(lo+hi)/2
            x=3*(1-u)**2*u*x1+3*(1-u)*u*u*x2+u**3
            if x<t: lo=u
            else: hi=u
        return 3*(1-u)**2*u*y1+3*(1-u)*u*u*y2+u**3
    return f
ease_out, ease_io = bez(0,0,.58,1), bez(.42,0,.58,1)

anims = {}
def anim(key, frm, to, dur, exec_, delay=0, playback=0, repeat=False, path=ease_out):
    anims[key] = dict(t=-delay, dir=1, frm=frm, to=to, dur=dur, ex=exec_, pb=playback, rep=repeat, path=path)
def step_anims(dt):
    for key in list(anims):
        a = anims.get(key)
        if a is None: continue
        a['t'] += dt
        if a['t'] < 0: continue
        d = a['dur'] if a['dir']==1 else a['pb']
        p = min(a['t']/d, 1)
        e = a['path'](p)
        v = a['frm']+(a['to']-a['frm'])*e if a['dir']==1 else a['to']+(a['frm']-a['to'])*e
        a['ex'](v)
        if p >= 1:
            if a['dir']==1 and a['pb']: a['dir']=-1; a['t']=0
            elif a['rep']: a['dir']=1; a['t']=0
            else: anims.pop(key, None)

mix = lambda a,b,m: tuple(round((x*m+y*(255-m))/255) for x,y in zip(a,b))
tint = lambda c: mix(c,(0,0,0),50)

S = dict(state='idle', color=C_GRAY, done=0, total=0, segW=0, active=-1, pct=0,
         start=0, stext='Ожидание', title='', step='', stepOpa=1, dotOpa=1, time='00:00')
fillW=[0]*MAX_SEG; fillOpa=[1]*MAX_SEG; segBg=[C_EMPTY]*MAX_SEG
col = {'from':C_GRAY,'to':C_GRAY}
NOW=[0.0]

def set_(d,k):
    def f(v): d[k]=v
    return f

def accent_to(target):
    col['from']=S['color']; col['to']=target
    def ex(v):
        S['color']=mix(col['to'],col['from'],v)
        if S['active']>=0: segBg[S['active']]=mix(S['color'],(0,0,0),40)
    anim('color',0,255,500,ex)

def pulse(key, setter, period):
    anim(key,255,76,period,lambda v: setter(v/255),playback=period,repeat=True,path=ease_io)
def pulse_stop(key, setter):
    anims.pop(key,None); setter(1)

def anim_width(i,to,delay):
    anims.pop('w%d'%i,None)
    if fillW[i]==to: return
    anim('w%d'%i,fillW[i],to,450,lambda v,i=i: fillW.__setitem__(i,v),delay=delay)

def layout(total):
    old=S['segW']; S['segW']=(W-2*M-GAP*(total-1))//total
    for i in range(MAX_SEG):
        anims.pop('w%d'%i,None)
        fillW[i]= fillW[i]*S['segW']/old if (i<total and old) else 0

def apply(st,title,step,done,total):
    total=max(1,min(MAX_SEG,total)); done=max(0,min(total,done))
    if st=='done': done=total
    prev=S['done']
    if active_st(st) and not active_st(S['state']): S['start']=NOW[0]; S['time']='00:00'
    if title is not None: S['title']=title
    if step is not None and step!=S['step']:
        S['step']=step; anim('step',0,1,300,set_(S,'stepOpa'))
    if total!=S['total']: layout(total); S['total']=total
    old=S['active']; S['active']= done if (active_st(st) and done<total) else -1
    if old>=0 and old!=S['active']:
        segBg[old]=C_EMPTY; pulse_stop('p%d'%old, lambda v,o=old: fillOpa.__setitem__(o,v))
    if st!=S['state']:
        S['stext']=STATES[st][1]; accent_to(STATES[st][0])
    if S['active']>=0: segBg[S['active']]=mix(S['color'],(0,0,0),40)
    S['state']=st
    for i in range(total):
        tgt = S['segW'] if i<done else (S['segW']*2//5 if i==S['active'] else 0)
        dl = (i-prev)*70 if (st=='done' and i>=prev) else 0
        anim_width(i,tgt,dl)
    if active_st(st):
        per = 450 if st=='wait' else 900
        pulse('dot',set_(S,'dotOpa'),per)
        if S['active']>=0:
            k=S['active']; pulse('p%d'%k, lambda v,k=k: fillOpa.__setitem__(k,v), per)
    else:
        pulse_stop('dot',set_(S,'dotOpa'))
    S['done']=done
    to=done*100//total
    if S['pct']!=to: anim('pct',S['pct'],to,600,lambda v: S.__setitem__('pct',round(v)))

def ellipsize(d,text,font,maxw):
    if d.textlength(text,font=font)<=maxw: return text
    s=text
    while s and d.textlength(s+'…',font=font)>maxw: s=s[:-1]
    return s+'…'

def draw():
    im=Image.new('RGB',(W*K,H*K),(0,0,0)); d=ImageDraw.Draw(im)
    c=S['color']
    tw=d.textlength(S['stext'],font=f_small)/K
    pw=14+12+10+tw+16
    pill=tint(c)
    d.rounded_rectangle([M*K,16*K,(M+pw)*K,48*K],radius=16*K,fill=pill)
    dot=mix(c,pill,round(255*S['dotOpa']))
    cx,cy=(M+20)*K,32*K
    d.ellipse([cx-6*K,cy-6*K,cx+6*K,cy+6*K],fill=dot)
    d.text(((M+36)*K,33*K),S['stext'],font=f_small,fill=c,anchor='lm')
    d.text(((W-M)*K,33*K),S['time'],font=f_small,fill=C_GRAY,anchor='rm')
    d.text((M*K,64*K),ellipsize(d,S['title'],f_title,(W-2*M)*K),font=f_title,fill=C_TEXT,anchor='la')
    d.text((M*K,108*K),ellipsize(d,S['step'],f_small,(W-2*M)*K),font=f_small,
           fill=mix(C_GRAY,(0,0,0),round(255*S['stepOpa'])),anchor='la')
    for i in range(S['total']):
        x=M+i*(S['segW']+GAP)
        box=[x*K,BAR_Y*K,(x+S['segW'])*K-1,(BAR_Y+BAR_H)*K-1]
        d.rounded_rectangle(box,radius=7*K,fill=segBg[i])
        if fillW[i]>0.5:
            mask=Image.new('L',im.size,0); md=ImageDraw.Draw(mask)
            md.rounded_rectangle(box,radius=7*K,fill=255)
            md.rectangle([(x+fillW[i])*K,0,im.size[0],im.size[1]],fill=0)
            fc=mix(c,segBg[i],round(255*fillOpa[i]))
            im.paste(Image.new('RGB',im.size,fc),(0,0),mask)
    cnt='%d/%d'%(S['done'],S['total'])
    d.text((M*K,218*K),cnt,font=f_big,fill=C_TEXT,anchor='ls')
    cw=d.textlength(cnt,font=f_big)/K
    d.text(((M+cw+12)*K,214*K),'задач готово',font=f_small,fill=C_GRAY,anchor='ls')
    d.text(((W-M)*K,218*K),'%d%%'%S['pct'],font=f_big,fill=c,anchor='rs')
    return im.resize((W,H),Image.LANCZOS)

# ---- сценарий ----
STEPS = TH['steps']
TITLE = TH['title']
plan = len(STEPS)
def ev_start(): apply('start', TITLE, 'Думает…', 0, 1)
def ev_step():
    if S['state'] == 'start':
        apply('work', None, STEPS[0], 0, plan)
        return
    dd = min(S['done'] + 1, S['total'])
    apply('work', None, STEPS[dd] if dd < S['total'] else 'Проверяю результат', dd, S['total'])
def ev_wait(): apply('wait', None, TH['ask'], S['done'], S['total'])
def ev_done(): apply('done', None, 'Задача выполнена', S['total'], S['total'])

seq = [(600, ev_start)]
t = 600 + 2500
for k in range(plan + 1):
    seq.append((t, ev_step)); t += 2000
    if k == 2:
        seq.append((t, ev_wait)); t += 2500
seq.append((t, ev_done))
END = t + 3500

apply('idle', 'Жду задачу', 'Отправьте задачу агенту', 0, 1)
anims.clear(); S['color'] = C_GRAY; S['stepOpa'] = 1

FPS = 20; dt = 1000 / FPS
frames = []; i = 0; tm = 0.0
while tm <= END:
    while i < len(seq) and seq[i][0] <= tm:
        seq[i][1](); i += 1
    step_anims(dt); NOW[0] = tm
    if active_st(S['state']):
        s = int((tm - S['start']) / 1000); S['time'] = '%02d:%02d' % (s // 60, s % 60)
    frames.append(draw()); tm += dt

out = ARGS.out or os.path.join(DOCS, f'{ARGS.theme}_task.gif')
pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
pal[0].save(out, save_all=True, append_images=pal[1:], duration=int(dt), loop=0, optimize=True, disposal=1)
print(f'{len(frames)} кадров → {out}')
