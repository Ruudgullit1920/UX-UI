"""Create tightly framed stakeholder evidence without changing raw captures."""

from __future__ import annotations

from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "shared" / "audits" / "authacceptance-4-209-241-167-20260929"
RAW = AUDIT / "screenshots"
OUT = AUDIT / "report" / "evidence" / "cropped"

RED = "#c62828"
WHITE = "#ffffff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def mark(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label_text: str | None = None) -> None:
    draw.rectangle(box, outline=RED, width=4)
    if label_text:
        text_font = font(16, True)
        x, y = box[0], max(2, box[1] - 25)
        left, top, right, bottom = draw.textbbox((x, y), label_text, font=text_font)
        draw.rounded_rectangle((left - 5, top - 3, right + 5, bottom + 3), radius=4, fill=RED)
        draw.text((x, y), label_text, font=text_font, fill=WHITE)


def cropped(source: Path, box: tuple[int, int, int, int]) -> Image.Image:
    with Image.open(source) as image:
        width, height = image.size
        left, top, right, bottom = box
        return image.convert("RGBA").crop((max(0, left), max(0, top), min(width, right), min(height, bottom)))


def save(image: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT / name, quality=95, optimize=True)


def mobile() -> None:
    # A 16:9 slice keeps the clipped workspace controls legible at the same
    # presentation size as every other issue-evidence screen.
    image = cropped(RAW / "targeted_followup" / "mobile_final.png", (0, 0, 390, 844))
    draw = ImageDraw.Draw(image)
    mark(draw, (244, 548, 388, 765), "Clipped action area")
    draw.line([(386, 18), (386, 826)], fill=RED, width=4)
    save(image, "issue-01-mobile-cropped.png")


def error() -> None:
    image = cropped(RAW / "manual_review" / "ai_analysis.png", (208, 36, 1648, 880))
    save(image, "issue-02-error-cropped.png")


def contrast() -> None:
    # Keep the dark navigation, selected yellow state, and red/green status
    # treatments together with their low-contrast labels.
    image = cropped(RAW / "pages" / "4.209.241.167" / "Home" / "page" / "main.png", (0, 90, 1440, 900))
    draw = ImageDraw.Draw(image)
    mark(draw, (20, 18, 135, 55), "Muted text")
    mark(draw, (265, 280, 1216, 314), "Search label")
    mark(draw, (270, 522, 430, 550), "Error label")
    mark(draw, (1330, 495, 1405, 525), "Error status")
    mark(draw, (1330, 627, 1405, 655), "Success status")
    save(image, "issue-03-contrast-cropped.png")


def language() -> None:
    # This tight region visibly pairs French UI chrome with Search, Success,
    # Failed, ERROR, and SUCCESS labels.
    image = cropped(RAW / "pages" / "4.209.241.167" / "Home" / "page" / "main.png", (240, 450, 1420, 840))
    draw = ImageDraw.Draw(image)
    mark(draw, (22, 5, 975, 41), "English: Search by TDR name...")
    mark(draw, (103, 55, 280, 88), "English: Success / Failed")
    mark(draw, (28, 170, 175, 200), "English: ERROR")
    mark(draw, (1088, 140, 1165, 170), "English: ERROR")
    mark(draw, (1088, 272, 1165, 302), "English: SUCCESS")
    save(image, "issue-04-language-cropped.png")


def password_control() -> None:
    image = cropped(RAW / "public_auth" / "registration-1440.png", (520, 250, 1400, 760))
    save(image, "issue-05-password-control-cropped.png")


def required_guidance() -> None:
    image = cropped(RAW / "public_auth" / "registration-1440.png", (520, 250, 1400, 760))
    save(image, "issue-06-required-guidance-cropped.png")


def main() -> None:
    mobile()
    error()
    contrast()
    language()
    password_control()
    required_guidance()
    print(f"Cropped stakeholder evidence written to: {OUT}")


if __name__ == "__main__":
    main()
