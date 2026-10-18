#!/usr/bin/env python3
"""
Перерисовать все гифки README из настоящего кода прошивки — для обеих тем.

    python tools/sim/render_docs.py                  # всё: 2 языка × 2 темы
    python tools/sim/render_docs.py task error       # только эти
    python tools/sim/render_docs.py --lang ru task   # только русский

Кладёт файлы в docs/firmware/<en|ru>/<claude|codex>/ и docs/firmware/<en|ru>/ (общие).
Вариант Codex получается из сценария заменой "agent":"claude" → "codex"
и сцены ожидания robot → cursor (сцена Codex по умолчанию). Английский вариант —
переводом текстов задач по таблице EN ниже и полем "lang" для подписей платы.
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

FPS = 20                   # README: 20 кадров/с выглядят так же, а весят меньше
BOTH = ('claude', 'codex')
LANGS = ('en', 'ru')

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


# Тексты задач в сценариях написаны по-русски; для английских гифок — перевод
EN = {
    "Думает…": "Thinking…", "Жду задачу": "Waiting for a task", "Задача выполнена": "Task complete",
    "Запускаю pytest": "Running pytest", "Запускаю тесты": "Running tests",
    "Изучаю структуру проекта": "Exploring the project",
    "Исследуй кодовую базу и предложи план": "Explore the codebase and propose a plan",
    "Ищу другой способ": "Trying another way", "Ищу мусор": "Looking for junk",
    "Контекст сжат, продолжаю": "Context compacted, going on",
    "Лимит запросов, пауза": "Rate limited, pausing", "Новая задача": "New task",
    "Обнови документацию": "Update the docs", "Обнови зависимости": "Update dependencies",
    "Обновляю логику токенов": "Updating token logic", "Отправьте задачу агенту": "Send a task to the agent",
    "Отрефактори модуль авторизации": "Refactor the auth module", "Ошибка: $ npm test": "Error: $ npm test",
    "Пишу README.md": "Writing README.md", "Пишу тесты": "Writing tests",
    "Почини падающие тесты": "Fix the failing tests", "Почисти временные файлы": "Clean up temp files",
    "Правлю модуль авторизации": "Editing the auth module", "Правлю парсер дат": "Fixing the date parser",
    "Разрешить запись README.md?": "Allow writing README.md?",
    "Разрешить запуск npm test?": "Allow running npm test?",
    "Разрешить: $ git push --force": "Allow: $ git push --force",
    "Разрешить: $ npm install": "Allow: $ npm install", "Разрешить: $ rm -rf build/": "Allow: $ rm -rf build/",
    "Сжимаю контекст (авто)": "Compacting context (auto)", "Собираю план": "Building a plan",
    "Субагент: поиск по модулям": "Subagent: searching modules", "Удаляю build/": "Removing build/",
    "Устанавливаю пакеты": "Installing packages", "Читаю package.json": "Reading package.json",
}


def variant(text, theme, lang):
    if theme == 'codex':
        text = re.sub(r'"agent":\s*"claude"', '"agent":"codex"', text)
        text = re.sub(r'"idle":\s*"robot"', '"idle":"cursor"', text)
    if lang == 'en':
        def tr(m):
            src = m.group(1)
            if re.search('[А-Яа-яЁё]', src) and src not in EN:
                raise SystemExit(f'нет перевода для сценария: {src!r} — добавьте в EN')
            return '"' + EN.get(src, src) + '"'
        text = '\n'.join(l if l.lstrip().startswith('#') else re.sub(r'"([^"]*)"', tr, l)
                         for l in text.split('\n'))
    return f'0 {{"lang":"{lang}"}}\n' + text          # подписи платы — на том же языке


def out_path(name, theme, png, lang):
    base = os.path.join(OUT, lang)
    folder = base if theme is None else os.path.join(base, theme)
    os.makedirs(folder, exist_ok=True)
    name = name.replace('idle_codex_cursor', 'idle_cursor')
    return os.path.join(folder, name + ('.png' if png else '.gif'))


def run(exe, name, theme, lang):
    scn, (lo, hi), _, png_at = JOBS[name]
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'scenario.txt')
        with open(os.path.join(SCN, scn), encoding='utf-8') as f:
            text = variant(f.read(), theme, lang)
        with open(src, 'w', encoding='utf-8') as f:
            f.write(text)
        raw = os.path.join(tmp, 'frames.rgb565')
        subprocess.run([exe, src, raw, str(FPS), str(int(hi * 1000)), str(int(lo * 1000))],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        dst = out_path(name, theme, png_at is not None, lang)
        gif = dst if png_at is None else os.path.join(tmp, 'x.gif')
        cmd = [sys.executable, os.path.join(HERE, 'frames_to_gif.py'), raw, gif, '--fps', str(FPS)]
        if png_at is not None:
            cmd += ['--png-at', str(round(png_at - lo, 3))]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        if png_at is not None:
            os.replace(os.path.join(tmp, f'x_{round(png_at - lo, 3)}s.png'), dst)
    return os.path.relpath(dst, ROOT)


def main():
    args = sys.argv[1:]
    langs = LANGS
    if '--lang' in args:
        i = args.index('--lang')
        langs = (args[i + 1],)
        del args[i:i + 2]
    names = args or list(JOBS)
    exe = build()
    tasks = [(n, t, lg) for lg in langs for n in names for t in JOBS[n][2]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path in pool.map(lambda job: run(exe, *job), tasks):
            print(path)


if __name__ == '__main__':
    main()
