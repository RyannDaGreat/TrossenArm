"""Locate image changes between decoded before/open/closed frames; not proof of robot motion."""

import cv2

before, opened, closed = [cv2.imread(f"agents/.scratchpad/gripper-{name}.png")
                          for name in ("before", "open", "closed")]
changed = cv2.cvtColor(cv2.absdiff(before, opened), cv2.COLOR_BGR2GRAY)
noise = cv2.cvtColor(cv2.absdiff(before, closed), cv2.COLOR_BGR2GRAY)
excess = cv2.subtract(changed, noise)
smoothed = cv2.GaussianBlur(excess, (9, 9), 0)
print("Largest open-vs-return change:", cv2.minMaxLoc(smoothed), flush=True)
heat = cv2.applyColorMap(cv2.convertScaleAbs(smoothed, alpha=8), cv2.COLORMAP_JET)
assert cv2.imwrite("agents/.scratchpad/motion-difference.png", heat)
for name, (x, y, width, height) in {
    "foreground": (440, 400, 600, 320), "left": (190, 340, 240, 230),
    "background": (510, 40, 300, 190),
}.items():
    print(name, "open diff", cv2.mean(changed[y:y+height, x:x+width])[0],
          "return diff", cv2.mean(noise[y:y+height, x:x+width])[0])
