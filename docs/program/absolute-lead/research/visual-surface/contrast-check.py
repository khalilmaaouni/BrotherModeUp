"""WCAG 2.x relative luminance and contrast ratio, per
https://www.w3.org/TR/WCAG22/#dfn-relative-luminance and #dfn-contrast-ratio
Standard library only."""


def srgb_channel(c8):
    c = c8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexstr):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * srgb_channel(r)
            + 0.7152 * srgb_channel(g)
            + 0.0722 * srgb_channel(b))


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


LIGHT_PAGE = "#FFFFFF"
DARK_PAGE = "#12151A"

pairs = [
    # (label, foreground, background, floor)
    ("LIGHT body text on page", "#1A1D21", LIGHT_PAGE, 4.5),
    ("LIGHT muted text on page", "#575E68", LIGHT_PAGE, 4.5),

    ("LIGHT stop ink on stop tint", "#8C2D00", "#FDEFE8", 4.5),
    ("LIGHT stop ink on page", "#8C2D00", LIGHT_PAGE, 4.5),
    ("LIGHT stop rule on stop tint", "#D55E00", "#FDEFE8", 3.0),
    ("LIGHT stop rule on page", "#D55E00", LIGHT_PAGE, 3.0),

    ("LIGHT check ink on check tint", "#6B4400", "#FFF6E5", 4.5),
    ("LIGHT check ink on page", "#6B4400", LIGHT_PAGE, 4.5),
    ("LIGHT check rule on check tint", "#A06A00", "#FFF6E5", 3.0),
    ("LIGHT check rule on page", "#A06A00", LIGHT_PAGE, 3.0),

    ("LIGHT insight ink on insight tint", "#00436B", "#EAF3FA", 4.5),
    ("LIGHT insight ink on page", "#00436B", LIGHT_PAGE, 4.5),
    ("LIGHT insight rule on insight tint", "#0072B2", "#EAF3FA", 3.0),
    ("LIGHT insight rule on page", "#0072B2", LIGHT_PAGE, 3.0),

    ("LIGHT done ink on done tint", "#00543A", "#E8F6F0", 4.5),
    ("LIGHT done ink on page", "#00543A", LIGHT_PAGE, 4.5),
    ("LIGHT done rule on done tint", "#009E73", "#E8F6F0", 3.0),
    ("LIGHT done rule on page", "#009E73", LIGHT_PAGE, 3.0),

    ("LIGHT idle ink on idle tint", "#3F4650", "#F1F2F4", 4.5),
    ("LIGHT idle rule on page", "#767B84", LIGHT_PAGE, 3.0),

    ("DARK body text on page", "#E9ECF1", DARK_PAGE, 4.5),
    ("DARK muted text on page", "#A7AEB9", DARK_PAGE, 4.5),

    ("DARK stop ink on stop tint", "#FFA582", "#2A1710", 4.5),
    ("DARK stop ink on page", "#FFA582", DARK_PAGE, 4.5),
    ("DARK stop rule on page", "#FF7A47", DARK_PAGE, 3.0),

    ("DARK check ink on check tint", "#F0B95A", "#2A2110", 4.5),
    ("DARK check ink on page", "#F0B95A", DARK_PAGE, 4.5),
    ("DARK check rule on page", "#E69F00", DARK_PAGE, 3.0),

    ("DARK insight ink on insight tint", "#7FC4F5", "#0F1E2A", 4.5),
    ("DARK insight ink on page", "#7FC4F5", DARK_PAGE, 4.5),
    ("DARK insight rule on page", "#56B4E9", DARK_PAGE, 3.0),

    ("DARK done ink on done tint", "#5FD3AE", "#0E2018", 4.5),
    ("DARK done ink on page", "#5FD3AE", DARK_PAGE, 4.5),
    ("DARK done rule on page", "#3FBF97", DARK_PAGE, 3.0),

    ("DARK idle ink on page", "#A7AEB9", DARK_PAGE, 4.5),
    ("DARK idle rule on page", "#767B84", DARK_PAGE, 3.0),

    # mermaid node fills: text on node fill, and node stroke on canvas
    ("LIGHT node text on neutral node fill", "#1A1D21", "#EFF1F4", 4.5),
    ("LIGHT node stroke on page", "#5B6470", LIGHT_PAGE, 3.0),
    ("DARK node text on neutral node fill", "#E9ECF1", "#1E242C", 4.5),
    ("DARK node stroke on page", "#8A93A0", DARK_PAGE, 3.0),
]

worst = []
for label, fg, bg, floor in pairs:
    r = ratio(fg, bg)
    ok = "PASS" if r >= floor else "FAIL"
    if r < floor:
        worst.append((label, r, floor))
    print(f"{ok}  {r:6.2f}:1  (floor {floor})  {label}  {fg} on {bg}")

print()
print("failures:", len(worst))
for w in worst:
    print("  ", w)

# independent sanity check of the maths: known reference values
print()
print("sanity black/white  expect 21.00 ->", round(ratio("#000000", "#FFFFFF"), 2))
print("sanity #767676/white expect ~4.54 ->", round(ratio("#767676", "#FFFFFF"), 2))
print("sanity #0072B2/white ->", round(ratio("#0072B2", "#FFFFFF"), 2))
