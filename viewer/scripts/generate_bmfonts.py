#!/usr/bin/env python3
"""
BMFont Generator for ALC Desktop Viewer
Generates pixel-perfect, artifact-free AngelCode .fnt and .png assets from Segoe UI Bold.
Ensures pure white RGB across all texels to eliminate OpenGL black-halo blending artifacts.
"""

import os
from PIL import Image, ImageFont

CHAR_SET = [
    # ASCII 32 to 126
    *(chr(i) for i in range(32, 127)),
    # Universal HUD Symbols
    '\u25cf', # ● Black circle
    '\u25cb', # ○ White circle
    '\u25a0', # ■ Black square
    '\u25b2', # ▲ Up triangle
    '\u25bc', # ▼ Down triangle
    '\u25c0', # ◀ Left triangle
    '\u25b6', # ▶ Right triangle (Play)
    '\u23f8', # ⏸ Pause
    '\u23ed', # ⏭ Next / Step
    '\u2713', # ✓ Checkmark
    '\u2715', # ✕ Close X
    '\u00b0', # ° Degree
    '\u00b1', # ± Plus-minus
    '\u2022', # • Bullet
    '\u2026', # … Ellipsis
    '\u2192', # → Right arrow
    '\u2190', # ← Left arrow
    '\u2191', # ↑ Up arrow
    '\u2193', # ↓ Down arrow
    '\u263c', # ☼ Sun
    '\u2248', # ≈ Waves
    '\u2018', # ‘ Left single quote
    '\u2019', # ’ Right single quote / apostrophe
    '\u201c', # “ Left double quote
    '\u201d', # ” Right double quote
    '\u2013', # – En dash
    '\u2014', # — Em dash
    '\u203a', # › Single right chevron
    '\u2039', # ‹ Single left chevron
    '\u00bb', # » Right double angle
    '\u00ab', # « Left double angle
]

def generate_font(font_path, font_size, out_fnt, out_png, face_name="Segoe UI Bold", tex_w=512, tex_h=256):
    font = ImageFont.truetype(font_path, font_size)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent + 2
    base = ascent + 1

    glyphs = []
    for ch in CHAR_SET:
        char_id = ord(ch)
        length = font.getlength(ch)
        xadvance = int(round(length))

        if ch == ' ':
            # Ensure comfortable space width
            space_adv = max(xadvance, int(round(font_size * 0.32)))
            glyphs.append({
                'id': char_id,
                'ch': ch,
                'width': 0,
                'height': 0,
                'xoffset': 0,
                'yoffset': 0,
                'xadvance': space_adv,
                'image': None
            })
            continue

        try:
            bbox = font.getbbox(ch)
            mask = font.getmask(ch, mode='L')
            left, top, right, bottom = bbox
            w, h = right - left, bottom - top

            # Guarantee spacing so adjacent glyphs never collide or touch
            xadvance = max(xadvance, w + 1)

            if w <= 0 or h <= 0 or mask.size[0] <= 0 or mask.size[1] <= 0:
                glyphs.append({
                    'id': char_id,
                    'ch': ch,
                    'width': 0,
                    'height': 0,
                    'xoffset': left,
                    'yoffset': top,
                    'xadvance': xadvance,
                    'image': None
                })
                continue

            # Pure white RGB (255, 255, 255) with antialiased alpha directly from FreeType
            # This completely avoids dark haloing / dirty borders in OpenGL
            alpha_img = Image.frombytes('L', mask.size, bytes(mask))
            glyph_img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            glyph_img.putalpha(alpha_img)

            glyphs.append({
                'id': char_id,
                'ch': ch,
                'width': w,
                'height': h,
                'xoffset': left,
                'yoffset': top,
                'xadvance': xadvance,
                'image': glyph_img
            })
        except Exception as e:
            print(f"Skipping char {hex(char_id)}: {e}")

    # Pack into texture with 4px padding between glyphs
    padding = 4
    cur_x = padding
    cur_y = padding
    max_row_h = 0

    packed_glyphs = []
    for g in glyphs:
        if 'image' not in g or g['image'] is None:
            g['x'] = 0
            g['y'] = 0
            packed_glyphs.append(g)
            continue

        w, h = g['width'], g['height']
        if cur_x + w + padding > tex_w:
            cur_x = padding
            cur_y += max_row_h + padding
            max_row_h = 0

        if cur_y + h + padding > tex_h:
            tex_h *= 2
            print(f"Expanded texture height to {tex_h} for {face_name} {font_size}")

        g['x'] = cur_x
        g['y'] = cur_y
        max_row_h = max(max_row_h, h)
        cur_x += w + padding
        packed_glyphs.append(g)

    # Initialize texture with pure white RGB (255, 255, 255) and 0 alpha
    # When OpenGL interpolates edges, it stays pure white without black bleed
    tex = Image.new('RGBA', (tex_w, tex_h), (255, 255, 255, 0))
    for g in packed_glyphs:
        if 'image' in g and g['image'] is not None:
            tex.paste(g['image'], (g['x'], g['y']))

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    tex.save(out_png)
    print(f"Saved texture: {out_png} ({tex_w}x{tex_h})")

    # Write .fnt file (AngelCode BMFont format)
    png_filename = os.path.basename(out_png)
    lines = [
        f'info face="{face_name}" size={font_size} bold=1 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1',
        f'common lineHeight={line_height} base={base} scaleW={tex_w} scaleH={tex_h} pages=1 packed=0',
        f'page id=0 file="{png_filename}"',
        f'chars count={len(packed_glyphs)}'
    ]

    for g in packed_glyphs:
        lines.append(
            f"char id={g['id']} x={g.get('x', 0)} y={g.get('y', 0)} "
            f"width={g['width']} height={g['height']} "
            f"xoffset={g['xoffset']} yoffset={g['yoffset']} "
            f"xadvance={g['xadvance']} page=0 chnl=15"
        )

    with open(out_fnt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Saved fnt descriptor: {out_fnt} ({len(packed_glyphs)} glyphs)")


def main():
    target_dir = os.path.abspath("viewer/src/main/resources/fonts")
    os.makedirs(target_dir, exist_ok=True)

    bold_ttf = "C:/Windows/Fonts/tahomabd.ttf"

    print("Generating font-large (19pt Bold Tahoma)...")
    generate_font(
        font_path=bold_ttf,
        font_size=19,
        out_fnt=os.path.join(target_dir, "font-large.fnt"),
        out_png=os.path.join(target_dir, "font-large.png"),
        face_name="Tahoma Bold",
        tex_w=512, tex_h=256
    )

    print("Generating font-mid (15pt Bold Tahoma)...")
    generate_font(
        font_path=bold_ttf,
        font_size=15,
        out_fnt=os.path.join(target_dir, "font-mid.fnt"),
        out_png=os.path.join(target_dir, "font-mid.png"),
        face_name="Tahoma Bold",
        tex_w=512, tex_h=256
    )

    print("Generating font-small (13pt Bold Tahoma)...")
    generate_font(
        font_path=bold_ttf,
        font_size=13,
        out_fnt=os.path.join(target_dir, "font-small.fnt"),
        out_png=os.path.join(target_dir, "font-small.png"),
        face_name="Tahoma Bold",
        tex_w=512, tex_h=256
    )

    print("All font assets successfully generated with pure white channels!")

if __name__ == "__main__":
    main()
