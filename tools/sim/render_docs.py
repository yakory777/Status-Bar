#!/usr/bin/env python3
"""
Перерисовать все гифки README из настоящего кода прошивки — для обеих тем.

    python tools/sim/render_docs.py            # всё
    python tools/sim/render_docs.py task error # только эти

Кладёт файлы в docs/firmware/claude/, docs/firmware/codex/ и docs/firmware/ (общие).
Вариант Codex получается из сценария заменой "agent":"claude" → "codex"
и сцены ожидания robot → cursor (сцена Codex по умолчанию).
"""
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCN = os.path.join(HERE, 'scenarios')
OUT = os.path.join(ROOT, 'docs', 'firmware')
sys.path.insert(0, HERE)
from render import build  # noqa: E402

FPS = 30
BOTH = ('claude', 'codex')

# имя: (сценарий, окно «от-до» в секундах, темы, кадр в PNG вместо GIF)
JOBS = {
    'task':        ('basic.txt',             (2.5, 20.5), BOTH, None),
    'error':       ('error.txt',             (2.5, 13),   BOTH, None),
    'compact':     ('compact_subagents.txt', (2.5, 13),   BOTH, None),
    'wait':        ('wait_escalation.txt',   (57, 67),    BOTH, None),
    'link_lost':   ('link_lost.txt',         (2.5, 17),   BOTH, None),
    'battery':     ('charging_pairing.txt',  (2.5, 11),   BOTH, None),
    'button':      ('button.txt',            (2.5, 20),   BOTH, None),
    'transitions': ('idle_transitions.txt',  (12.5, 26.5), BOTH, None),
    'sleep':       ('sleep.txt',             (597, 605),  BOTH, None),
    'pairing':     ('charging_pairing.txt',  (12, 13),    BOTH, 12.5),
    'idle_robot':  ('idle_claude_robot.txt', (2.5, 13),   ('claude',), None),
    'idle_cursor': ('idle_claude_cursor.txt', (2.5, 13),  ('claude',), None),
    'idle_codex_cursor': ('idle_codex_cursor.txt', (2.5, 13), ('codex',), None),
    'idle_typist': ('idle_codex_typist.txt', (2.5, 10.5), ('codex',), None),
    'splash':      ('idle_transitions.txt',  (0, 3),      (None,), None),
    'sessions':    ('sessions.txt',          (2.5, 13),   (None,), None),
}


def variant(text, theme):
    if theme != 'codex':
        return text
    text = re.sub(r'"agent":\s*"claude"', '"agent":"codex"', text)
    return re.sub(r'"idle":\s*"robot"', '"idle":"cursor"', text)


def out_path(name, theme, png):
    folder = OUT if theme is None else os.path.join(OUT, theme)
    os.makedirs(folder, exist_ok=True)
    name = name.replace('idle_codex_cursor', 'idle_cursor')
    return os.path.join(folder, name + ('.png' if png else '.gif'))


def run(exe, name, theme):
    scn, (lo, hi), _, png_at = JOBS[name]
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'scenario.txt')
        with open(os.path.join(SCN, scn), encoding='utf-8') as f:
            text = variant(f.read(), theme)
        with open(src, 'w', encoding='utf-8') as f:
            f.write(text)
        raw = os.path.join(tmp, 'frames.rgb565')
        subprocess.run([exe, src, raw, str(FPS), str(int(hi * 1000)), str(int(lo * 1000))],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        dst = out_path(name, theme, png_at is not None)
        gif = dst if png_at is None else os.path.join(tmp, 'x.gif')
        cmd = [sys.executable, os.path.join(HERE, 'frames_to_gif.py'), raw, gif, '--fps', str(FPS)]
        if png_at is not None:
            cmd += ['--png-at', str(round(png_at - lo, 3))]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        if png_at is not None:
            os.replace(os.path.join(tmp, f'x_{round(png_at - lo, 3)}s.png'), dst)
    return os.path.relpath(dst, ROOT)


def main():
    names = sys.argv[1:] or list(JOBS)
    exe = build()
    tasks = [(n, t) for n in names for t in JOBS[n][2]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path in pool.map(lambda nt: run(exe, *nt), tasks):
            print(path)


if __name__ == '__main__':
    main()
