#!/usr/bin/env python3
"""
Кадры RGB565 из agent_sim → GIF (и, по желанию, отдельные PNG).

    python tools/sim/frames_to_gif.py out.rgb565 out.gif [--fps 30] [--png-at 1.5,4.0]
"""
import argparse
import os
import shutil
import subprocess

from PIL import Image

W, H = 536, 240


def frames(path):
    size = W * H * 2
    with open(path, 'rb') as f:
        while True:
            raw = f.read(size)
            if len(raw) < size:
                return
            # RGB565 little-endian → RGB888
            im = Image.frombuffer('RGB', (W, H), raw, 'raw', 'BGR;16', 0, 1)
            yield im


def ffmpeg_gif(fr, dst, fps):
    """Общая палитра и перерисовка только изменившихся прямоугольников: гифка вдвое легче."""
    raw = b''.join(f.tobytes() for f in fr)
    flt = ('[0:v]split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];'
           '[b][p]paletteuse=dither=none:diff_mode=rectangle')
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                        '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-filter_complex', flt, dst],
                       input=raw)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--png-at', default='', help='секунды через запятую — сохранить кадры в PNG рядом с GIF')
    ap.add_argument('--clip', default='', help='вырезать фрагмент «от-до» в секундах, например 58-70')
    a = ap.parse_args()
    fr = list(frames(a.src))
    allfr = fr
    if a.clip:
        lo, hi = (float(x) for x in a.clip.split('-'))
        fr = fr[int(lo * a.fps):int(hi * a.fps)]
    if not fr:
        raise SystemExit('нет кадров')
    if not (shutil.which('ffmpeg') and ffmpeg_gif(fr, a.dst, a.fps)):
        pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in fr]
        pal[0].save(a.dst, save_all=True, append_images=pal[1:], duration=int(1000 / a.fps),
                    loop=0, optimize=True, disposal=1)
    base = os.path.splitext(a.dst)[0]
    for s in filter(None, a.png_at.split(',')):
        i = min(len(allfr) - 1, int(float(s) * a.fps))
        allfr[i].save(f'{base}_{s}s.png')
    print(f'{len(fr)} кадров → {a.dst}')


if __name__ == '__main__':
    main()
