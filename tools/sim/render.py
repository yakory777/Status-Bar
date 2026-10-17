#!/usr/bin/env python3
"""
Собрать симулятор (если нужно), прогнать сценарий через UI-код прошивки и сохранить GIF.

    python tools/sim/render.py tools/sim/scenarios/basic.txt docs/sim_basic.gif
    python tools/sim/render.py SCENARIO OUT.gif --png-at 2,5     # плюс кадры в PNG

Переменные LVGL_DIR и CJSON_DIR позволяют взять уже скачанные исходники.
"""
import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(ROOT, 'build', 'sim')


def build():
    args = ['cmake', '-S', HERE, '-B', BUILD, '-DCMAKE_BUILD_TYPE=Release']
    for var in ('LVGL_DIR', 'CJSON_DIR'):
        if os.environ.get(var):
            args.append(f'-D{var}={os.environ[var]}')
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['cmake', '--build', BUILD, '-j', str(os.cpu_count() or 2)], check=True,
                   stdout=subprocess.DEVNULL)
    return os.path.join(BUILD, 'agent_sim')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scenario')
    ap.add_argument('out')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--duration', type=int, help='мс; по умолчанию последнее событие + 3 с')
    ap.add_argument('--png-at', default='')
    ap.add_argument('--clip', default='', help='фрагмент «от-до» в секундах')
    a = ap.parse_args()

    exe = build()
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'frames.rgb565')
        duration, start = a.duration or 0, 0
        if a.clip:                                    # симулятор пишет только кадры из окна
            lo, hi = (float(x) for x in a.clip.split('-'))
            start, duration = int(lo * 1000), int(hi * 1000)
        cmd = [exe, a.scenario, raw, str(a.fps), str(duration), str(start)]
        subprocess.run(cmd, check=True)
        png_at = ','.join(str(round(float(x) - start / 1000, 3)) for x in a.png_at.split(',') if x)
        subprocess.run([sys.executable, os.path.join(HERE, 'frames_to_gif.py'), raw, a.out,
                        '--fps', str(a.fps), '--png-at', png_at], check=True)


if __name__ == '__main__':
    main()
