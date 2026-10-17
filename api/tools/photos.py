import io

from PIL import Image, ImageDraw, ImageFont


def photo(lines: list[str]) -> bytes:
    image = Image.new("RGB", (1024, max(576, 80 + len(lines) * 120)), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 60)
    for index, line in enumerate(lines):
        draw.text((60, 50 + index * 120), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return buffer.getvalue()
