# Renderer receipt

**Renderer:** `rsvg-convert version 2.62.3`.

The source diagram is `profile-evolution-codex-front-door.svg` with a fixed
1600 by 900 view box. The checked-in PNG was reproduced byte-for-byte from
that source with:

```bash
rsvg-convert --width 1600 --height 900 \
  profile-evolution-codex-front-door.svg \
  --output profile-evolution-codex-front-door.png
```

The SVG is the editable source. The PNG is the portable rendered copy used by
Markdown readers that do not display repository SVG files consistently.

## Portable source/render binding

| Source / render | Source SHA-256 | Render SHA-256 |
|---|---|---|
| `profile-evolution-codex-front-door.svg` / `profile-evolution-codex-front-door.png` | `b234ecd6051e02cfb6bfc2a07a71ea31cb753ab8b481bb13543f463c05168c01` | `be9dc7a21a256cbc2bedbbbcf223d1b773244a9c3b8a479d01c4000c859e3e42` |

Any source or render change requires rerendering, visual inspection, and new
digests.
