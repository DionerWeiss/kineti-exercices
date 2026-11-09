"""Kineti version of MakeHuman's female_casualsuit01 diffuse: Kineti-blue
t-shirt with the Kineti print on the chest, navy trousers. The cloth shading
of the original texture is kept (colour = brand colour x relative luminance).

    build/mocap-venv/bin/python tool/mixamo/suit_texture.py <diffuse.png> <shirt_print.png> <out.png>
"""

import sys

import numpy as np
from PIL import Image

SHIRT = np.array((8, 88, 162), float)    # same blue as the male character's shirt
TRIM = np.array((14, 52, 104), float)
PANTS = np.array((44, 57, 85), float)
LOGO_BOX = (1440, 300, 1790, 650)        # original chest logo (x0, y0, x1, y1)
PRINT_CENTRE = (1590, 470)
PRINT_SPAN = 330                         # print width on the body, pixels (vertical in UV)


def main(src, print_png, out):
    im = np.asarray(Image.open(src).convert('RGB')).astype(float)
    h, w, _ = im.shape
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = im.max(-1) - im.min(-1)
    cloth = sat > 18
    yy, xx = np.mgrid[0:h, 0:w]
    orange = cloth & (r > b + 40) & (r > 120)
    sleeves = (xx > 1480) & (yy > 1180) & ~((xx < 1580) & (yy < 1330))  # not the trouser edge beside them
    x0, y0, x1, y1 = LOGO_BOX
    logo = np.zeros_like(cloth)
    logo[y0:y1, x0:x1] = True
    shirt = (cloth & ((yy < 880) | sleeves)) | logo
    pants = cloth & ~shirt
    body = shirt & ~orange & ~logo
    ref = np.median(lum[body])
    rel = np.clip(lum / ref, 0.55, 1.35)
    rel[logo] = np.median(rel[body & (yy < 880) & (xx > 1300)])  # flat where the old logo was
    out_img = im.copy()
    out_img[body | (logo & shirt)] = SHIRT * rel[body | (logo & shirt)][:, None]
    out_img[orange & shirt & ~logo] = TRIM
    pref = np.median(lum[pants])
    out_img[pants] = PANTS * np.clip(lum[pants] / pref, 0.6, 1.5)[:, None]
    result = Image.fromarray(np.clip(out_img, 0, 255).astype(np.uint8))

    pr = Image.open(print_png).convert('RGBA')
    pr = pr.crop(pr.getbbox())
    scale = PRINT_SPAN / pr.width
    pr = pr.resize((PRINT_SPAN, int(pr.height * scale)), Image.LANCZOS).rotate(-90, expand=True)
    cx, cy = PRINT_CENTRE
    result.paste(pr, (cx - pr.width // 2, cy - pr.height // 2), pr)
    result.save(out)
    print('saved', out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
