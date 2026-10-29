"""Create a labeled montage of the four independently captured camera views."""
from PIL import Image, ImageDraw, ImageFont

PANEL_WIDTH, PANEL_HEIGHT = 640, 360
LABEL_HEIGHT = 54
VIEWS = [
    ("Top view", "418643070452"),
    ("Bottom view", "unidentified"),
    ("Left arm view", "418643070450"),
    ("Right arm view", "418643070460"),
]
montage = Image.new("RGB", (PANEL_WIDTH * 2, (PANEL_HEIGHT + LABEL_HEIGHT) * 2), "#111111")
draw = ImageDraw.Draw(montage)
font = ImageFont.load_default(size=19)
for index, (label, serial) in enumerate(VIEWS):
    image = Image.open(f"agents/.scratchpad/camera-{serial}.png")
    assert image.size == (1280, 720)
    x = index % 2 * PANEL_WIDTH
    y = index // 2 * (PANEL_HEIGHT + LABEL_HEIGHT)
    identity = f"Serial {serial}" if serial != "unidentified" else "USB serial not reported; session identity only"
    draw.text((x + 8, y + 4), label, font=font, fill="white")
    draw.text((x + 8, y + 28), identity, font=font, fill="white")
    montage.paste(image.resize((PANEL_WIDTH, PANEL_HEIGHT)), (x, y + LABEL_HEIGHT))
path = "agents/.scratchpad/four-camera-montage.png"
montage.save(path)
print(path, flush=True)
