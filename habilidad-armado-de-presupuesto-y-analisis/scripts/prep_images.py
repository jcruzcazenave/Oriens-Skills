# -*- coding: utf-8 -*-
"""
Helpers para preparar las imágenes de producto de la ficha técnica.

Objetivo: que las 4 imágenes (panel, inversor, estructura chapa, estructura techo
plano) queden sobre fondo BLANCO limpio, igual que la hoja.

Fuentes típicas:
  - Panel e inversor: extraer de la ficha técnica PDF del fabricante.
  - Estructuras: fotos/renders que pase el asesor.

Comandos útiles para extraer imágenes de un PDF (correr en shell):
    pdfimages -list ficha.pdf                 # listar imágenes y tamaños
    pdfimages -all ficha.pdf /tmp/out/x       # extraer todas (jpg/png + smask)
La imagen de producto suele ser la más grande (mayor width×height). Si tiene un
'smask' asociado, ese es el canal de transparencia (aplicarlo con apply_smask).

Funciones:
    whiten_bg(src, dst, thr=232)      -> tono crema/gris claro pasa a blanco puro
    apply_smask(rgb, smask, dst)      -> combina imagen + smask, recorta, fondo blanco
    trim_white(src, dst)              -> recorta márgenes blancos

Requiere: Pillow, numpy.
"""
import sys
from PIL import Image
import numpy as np


def _trim_alpha(im):
    a = np.array(im); al = a[:, :, 3]; ys, xs = np.where(al > 8)
    if len(xs) == 0:
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def whiten_bg(src, dst, thr=232, lift=1.0):
    """Pasa a blanco puro todo pixel casi-blanco/crema. Mantiene el producto.
    lift>1.0 aclara suavemente el resto (ej 1.04)."""
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(int)
    mask = a.min(axis=2) >= thr
    a[mask] = [255, 255, 255]
    if lift != 1.0:
        a = np.clip(a * lift, 0, 255)
    Image.fromarray(a.astype("uint8"), "RGB").save(dst)
    return dst


def apply_smask(rgb_path, smask_path, dst, thr=232):
    """Combina imagen RGB con su smask (transparencia), limpia halo crema a blanco
    y recorta al contenido. Ideal para renders con fondo transparente."""
    rgb = Image.open(rgb_path).convert("RGB")
    sm = Image.open(smask_path).convert("L").resize(rgb.size)
    rgba = rgb.convert("RGBA"); rgba.putalpha(sm)
    a = np.array(rgba).astype(int)
    light = a[:, :, :3].min(axis=2) >= thr
    a[light, 0:3] = 255
    im = Image.fromarray(a.astype("uint8"), "RGBA")
    im = _trim_alpha(im)
    im.save(dst)
    return dst


def trim_white(src, dst, thr=245):
    """Recorta márgenes blancos alrededor de un objeto sobre fondo blanco."""
    im = Image.open(src).convert("RGB")
    a = np.array(im)
    mask = a.min(axis=2) < thr
    ys, xs = np.where(mask)
    if len(xs):
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    im.save(dst)
    return dst


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "whiten":
        whiten_bg(sys.argv[2], sys.argv[3])
        print("whiten ->", sys.argv[3])
    elif len(sys.argv) >= 5 and sys.argv[1] == "smask":
        apply_smask(sys.argv[2], sys.argv[3], sys.argv[4])
        print("smask ->", sys.argv[4])
    elif len(sys.argv) >= 4 and sys.argv[1] == "trim":
        trim_white(sys.argv[2], sys.argv[3])
        print("trim ->", sys.argv[3])
    else:
        print(__doc__)
