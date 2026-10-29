"""Build side-by-side crops from real video frames for visual inspection; no image synthesis."""

from PIL import Image, ImageDraw

frames = [Image.open(f"agents/.scratchpad/gripper-{name}.png")
          for name in ("before", "open", "closed")]
# Real image regions: foreground jaws, left-side gripper, background gripper.
regions = {"upper-left": (0, 0, 260, 300),
           "foreground": (440, 400, 1040, 720),
           "left": (190, 340, 430, 570),
           "background": (510, 40, 810, 230)}
for name, box in regions.items():
    width, height = box[2] - box[0], box[3] - box[1]
    label_height = 24
    sheet = Image.new("RGB", (width * 3, height + label_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (frame, label) in enumerate(zip(frames, ("Before 4.5s", "Open target 8.1s", "Closed target 11.6s"))):
        sheet.paste(frame.crop(box), (index * width, label_height))
        draw.text((index * width, 4), label, fill="black")
    output = f"agents/.scratchpad/motion-{name}.png"
    sheet.save(output)
    print(output)
