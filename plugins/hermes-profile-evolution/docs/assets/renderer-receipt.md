# Renderer receipt

The source diagram is `profile-evolution-codex-front-door.svg` with a fixed
1600 by 900 view box. The checked-in PNG is rendered from that source with:

```bash
rsvg-convert --width 1600 --height 900 \
  profile-evolution-codex-front-door.svg \
  --output profile-evolution-codex-front-door.png
```

The SVG is the editable source. The PNG is the portable rendered copy used by
Markdown readers that do not display repository SVG files consistently.
