"""
WatermarkPro v2 — Tray Icon Generator (user_app/_icon.py)
Generates the system-tray PIL image programmatically.
"""


def make_tray_image(size: int = 64):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle background (dark blue)
    m = size // 8
    draw.ellipse([m, m, size - m, size - m], fill=(30, 60, 120, 230))

    # "W" letter
    fs = max(8, int(size * 0.50))
    try:
        font = ImageFont.truetype("arialbd.ttf", fs)
    except Exception:
        font = ImageFont.load_default()

    bb = draw.textbbox((0, 0), "W", font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((size - tw) // 2, (size - th) // 2), "W",
              font=font, fill=(200, 220, 255, 255))
    return img


def generate_ico(output_path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
        from pathlib import Path

        sizes = [256, 128, 64, 48, 32, 16]
        images = []
        for s in sizes:
            img  = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            pad  = max(2, s // 12)
            # Shield body
            cx = s // 2
            pts = [
                (cx - s // 2 + pad, pad),
                (cx + s // 2 - pad, pad),
                (cx + s // 2 - pad, pad + (s - 2 * pad) * 6 // 10),
                (cx,                pad + (s - 2 * pad)),
                (cx - s // 2 + pad, pad + (s - 2 * pad) * 6 // 10),
            ]
            for y in range(s):
                r = int(20 + (y / s) * 10)
                g = int(40 + (y / s) * 20)
                b = int(80 + (y / s) * 40)
                draw.line([(pad, y), (s - pad, y)], fill=(r, g, b, 200))
            draw.polygon(pts, outline=(100, 160, 255, 255))

            fs = max(8, int(s * 0.45))
            try:
                font = ImageFont.truetype("arialbd.ttf", fs)
            except Exception:
                font = ImageFont.load_default()
            bb = draw.textbbox((0, 0), "W", font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            draw.text(((s - tw) // 2, (s - th) // 2), "W",
                      font=font, fill=(220, 235, 255, 255))
            images.append(img)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        images[0].save(str(output_path), format="ICO",
                       sizes=[(s, s) for s in sizes],
                       append_images=images[1:])
        return True
    except Exception as e:
        print(f"Icon generation failed: {e}")
        return False
