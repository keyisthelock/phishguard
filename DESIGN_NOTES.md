# PhishGuard / editorial identity

The reference direction combines [Awwwards](https://www.awwwards.com/)' large typographic hierarchy and orderly layouts with the warm colors, analog presentation and playful circular composition observed on [Quang Dinh's portfolio](https://www.quangdinh.im/). This is an original adaptation for PhishGuard; no reference-site images, logos, source code or branded artwork were copied.

## Current visual system

- Warm ivory (#f0eee7), ink (#23231f), vermilion (#ee512c) and signal yellow (#f6ee53). The optional dark theme uses warm charcoal rather than navy.
- Full-width header and numbered navigation; mobile menu includes account access and closes with Escape.
- Oversized condensed poster typography, serif accents and small monospace annotations.
- Original CSS signal-lens illustration with concentric shapes, restrained light sweep and a yellow caution sticker. No external image assets or rendering library.
- Horizontal moving headline strip, stagger-free entrance motion and scroll reveals; all motion is disabled for reduced-motion preferences.
- A clear anchor from the hero to the real scanner. The app's message/URL modes, explanations, accounts, analytics, feedback and learning tools remain functional.
- A single active stylesheet, `static/editorial.css`; the superseded navy and glass stylesheets were removed. No third-party fonts or animation libraries are required.

The desktop layout was reviewed at 1440 × 1000; the mobile layout and menu at 390 × 844. Live message scanning was verified after the redesign. The full 28-test backend suite passed; account and guest smoke tests passed again after the final navigation adjustment. Azure remains deferred as documented in AZURE_SETUP.md.
