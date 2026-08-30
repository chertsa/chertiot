# CHERT Systems — Identity & Digital Design Guide

**Version 1.0** · Unified design system for all CHERT products
**Audience:** Claude Code and any engineer or agent building a CHERT website or system UI.

---

## 0. How to use this document

This is the **single source of truth** for the appearance and behavior of every CHERT digital product. It is written to be read directly by Claude Code.

**Rules of engagement:**

1. **Never invent values.** Every color, size, radius, and spacing value in a CHERT build must come from the token tables in this document. If a value is not here, it does not exist.
2. **Never hardcode a hex.** Reference the CSS custom property (`var(--chert-orange)`), never `#FF8651`.
3. **When this guide conflicts with a habit, this guide wins.** Do not substitute a familiar default (Bootstrap blue, Tailwind gray-500, a stock shadow) for a token defined here.
4. **Copy Section 10 verbatim.** The token stylesheet is not a suggestion — it ships as-is into every project.
5. **If a screen doesn't look like it belongs next to the other five products, it isn't finished.**

### Products in scope

| Domain | Product | Type | Purpose |
|---|---|---|---|
| `chertlearninghub.com` | CHERT Learning | platform portal | full features of collective opensource systems to run as on platofrm  | 

 

---

## 1. Identity

### 1.1 What CHERT means

Chert is a hard sedimentary rock — the stone early toolmakers knapped into blades and arrowheads. It is the original engineered material: naturally occurring, but useful only once it is deliberately shaped.

That idea is the whole brand. CHERT builds **foundational tools that are shaped, not assembled** — hard, precise, and made to be relied on. The identity should always feel *engineered and durable*, never *soft or trendy*.

### 1.2 Brand attributes

The system must express these five attributes. When making any design decision, check it against this list.

| Attribute | Means | Does not mean |
|---|---|---|
| **Foundational** | Bedrock, dependable, load-bearing | Boring, plain |
| **Crafted** | Deliberate, precise, hand-shaped | Fussy, ornamental |
| **Warm** | Human, approachable, earthen | Casual, playful |
| **Clear** | Direct, legible, unambiguous | Blunt, cold |
| **Unified** | One family, one login, one language | Uniform, monotonous |

### 1.3 Voice & tone

CHERT speaks like a skilled colleague explaining their work: **plain, active, specific.**

- **Active voice, always.** "Save changes" not "Changes will be saved."
- **Name things by what the user controls,** not how the system is built. "Notifications" not "webhook config."
- **Sentence case everywhere** except the wordmark and overlines.
- **Be specific over clever.** "Sync completed in 4s" beats "All done! 🎉"
- **Errors don't apologize and are never vague.** Say what happened and how to fix it.
- **An action keeps its name through the whole flow.** A button that says "Publish" produces a toast that says "Published."

**Voice examples:**

| Context | ✅ Write this | ❌ Not this |
|---|---|---|
| Empty state | "No video yet. Create your first one." | "Nothing to see here!" |
| Error | "Card fail. course does not exist any more." | "Oops! Something went wrong." |
| Button | "Create course" | "Submit" |
| Success | "test submited." | "Success! 🎉" |
| Loading | "Syncing training data…" | "Please wait…" |

### 1.4 Naming

- The company/system is **CHERT** (all caps) in the wordmark and headings.
- Products are **CHERT Learning Hub**,  
- In URLs, code, and lowercase UI contexts: `chertlearninghub `,  — one word, no space, no camelCase.
- Never write "Chert" in sentence case, "CHERTLearningHub", or "Chert-learninghub".

---

## 2. Logo & Marks

### 2.1 The arrowhead

The primary mark is the knapped chert arrowhead — a detailed line engraving. It carries the craft story and must never be simplified into a generic triangle.

**Usage:**

| Rule | Spec |
|---|---|
| Header size | 32 px tall (desktop), 28 px (mobile) |
| Minimum size | 20 px tall — below this, use the starburst instead |
| Clear space | Equal to the height of the "C" in the wordmark, on all sides |
| Placement | Top-left of header (LTR) / top-right (RTL) |
| With wordmark | Mark + 12 px gap + `CHERT` wordmark |

**Never:** recolor it, stretch it, rotate it, add shadows or glows, place it on a busy photo, re-draw it, or flip it in RTL.

### 2.2 The starburst

The 8-point starburst is the **secondary mark** and the system's workhorse accent. It comes from the brand's print identity and appears throughout the UI.

**Use it for:**

- Product card icons
- Loading indicators (rotating, 1.2s linear)
- Section dividers (centered, with hairlines either side)
- Empty-state illustrations
- The cross-product switcher trigger
- Favicon fallback at small sizes

**Spec:** thin strokes, `stroke-width: 3`, `stroke-linecap: round`, `currentColor` so it inherits context color.

```html
<svg class="chert-star" viewBox="0 0 100 100" fill="none" stroke="currentColor"
     stroke-width="3" stroke-linecap="round" aria-hidden="true">
  <line x1="50" y1="8"  x2="50" y2="38"/>
  <line x1="50" y1="62" x2="50" y2="92"/>
  <line x1="8"  y1="50" x2="38" y2="50"/>
  <line x1="62" y1="50" x2="92" y2="50"/>
  <line x1="22" y1="22" x2="40" y2="40"/>
  <line x1="60" y1="60" x2="78" y2="78"/>
  <line x1="78" y1="22" x2="60" y2="40"/>
  <line x1="40" y1="60" x2="22" y2="78"/>
</svg>
```

### 2.3 Product lockups

Each product uses the shared mark plus a lowercase product name. **There are no per-product logos and no per-product colors.** Unity is the point.

```
[arrowhead]  CHERT              ← corporate
[arrowhead]  chert|mail         ← product (all ink; orange reserved for fills)
```

---

## 3. Color

### 3.1 Brand palette

These five colors are the identity. They are derived directly from the CHERT print identity.

| Token | Hex | Name | Use |
|---|---|---|---|
| `--chert-orange` | `#FF8651` | CHERT Orange | Primary buttons, key fills, active states |
| `--chert-orange-deep` | `#F26B33` | Orange Deep | Button hover, underlines, icons on tinted fills — **not body text** (see §3.6) |
| `--chert-tan` | `#D2B082` | Tan | Sidebars, secondary surfaces, muted panels |
| `--chert-cream` | `#FFFAE4` | Cream | Default page background |
| `--chert-ink` | `#1A1A18` | Ink | Body text, headings, dark surfaces, footer |

### 3.2 Extended palette

| Token | Hex | Use |
|---|---|---|
| `--chert-surface` | `#FFFFFF` | Elevated surfaces (cards, inputs, modals) |
| `--chert-surface-alt` | `#FBF7EC` | Zebra rows, subtle fills |
| `--chert-border` | `#ECE0C2` | Default borders, dividers |
| `--chert-border-strong` | `#D9C9A4` | Emphasized borders |
| `--chert-muted` | `#6B6B66` | Secondary text, placeholders, captions |
| `--chert-orange-tint` | `#FDEEE4` | Callout fills, icon box backgrounds |

### 3.3 Functional colors

| Token | Hex | Tint (10%) | Use |
|---|---|---|---|
| `--chert-success` | `#10B981` | `#E7F8F2` | Confirmations, healthy status |
| `--chert-warning` | `#F59E0B` | `#FEF4E3` | Warnings, degraded status |
| `--chert-error` | `#EF4444` | `#FDECEC` | Errors, destructive actions |
| `--chert-info` | `#3B82F6` | `#EAF1FE` | Neutral information |

> Functional colors are for **status only**. Never use them decoratively — that's what the brand palette is for.

### 3.4 Dark surfaces

Used for the footer, and for dashboard chrome in data-heavy products (BI, Fleet).

| Token | Hex | Use |
|---|---|---|
| `--chert-dark` | `#151311` | Dark page/footer background |
| `--chert-dark-surface` | `#1B1815` | Cards on dark |
| `--chert-dark-border` | `#26221D` | Borders on dark |
| `--chert-dark-text` | `#F3EDE0` | Body text on dark |
| `--chert-dark-muted` | `#A89E8D` | Secondary text on dark |

On dark surfaces, `--chert-orange` is the accent and **passes contrast** for both text and fills.

### 3.5 The 60-30-10 rule

Every CHERT screen distributes color in this ratio:

- **60%** — Cream and white backgrounds/surfaces
- **30%** — Ink text and tan secondary surfaces
- **10%** — Orange, and **only** for primary actions and key accents

**Do not flood a screen with orange.** The book cover uses large orange fields; a web UI cannot. On screen, orange is a signal, not a surface.

### 3.6 Contrast & accessibility — mandatory

> **Critical:** The CHERT palette is warm and light. **Orange cannot carry text on cream — at any size.** This is the single most common way to break the system. All ratios below are computed against the actual token values; AA requires **4.5:1** for body text and **3.0:1** for large text (≥24px, or ≥19px bold) and UI boundaries.

| Foreground | Background | Ratio | Verdict |
|---|---|---|---|
| Orange `#FF8651` | Cream | **2.28** | ❌ **Never** — fails at every size |
| Orange-deep `#F26B33` | Cream | **2.89** | ❌ **Never** — fails even large-text (3.0) |
| Orange-deep `#F26B33` | White | **3.03** | ⚠️ **Large text only** (≥24px / ≥19px bold) |
| Ink `#1A1A18` | Cream | **16.64** | ✅ Any size |
| Ink `#1A1A18` | White | 17.55 | ✅ Any size |
| Ink `#1A1A18` | Surface-alt | 16.28 | ✅ Any size |
| Ink `#1A1A18` | Orange | **7.29** | ✅ Any size |
| Ink `#1A1A18` | Tan | **8.53** | ✅ Any size |
| Ink `#1A1A18` | Orange-tint | 15.38 | ✅ Any size |
| Muted `#6B6B66` | Cream | **5.11** | ✅ Any size |
| White `#FFFFFF` | Orange | **2.39** | ❌ **Fails** — see button rule below |
| Cream `#FFFAE4` | Ink | 16.64 | ✅ Any size |
| Orange `#FF8651` | Dark `#151311` | **7.75** | ✅ Any size |
| Dark-text `#F3EDE0` | Dark | 15.89 | ✅ Any size |
| Dark-muted `#A89E8D` | Dark | 7.01 | ✅ Any size |

**The operating rules — read these carefully:**

1. **Orange and orange-deep are fill colors, not text colors on light backgrounds.** Orange-deep on *cream* fails (2.89) even for large text. It only clears large-text AA on pure *white* (3.03), and only at ≥24px / ≥19px bold.
2. **All body text is `--chert-ink` or `--chert-muted`.** No exceptions on light surfaces.
3. **Primary button text must be `--chert-ink`, not white.** White on orange is 2.39 and fails; ink on orange is 7.29 and passes at any size. *This overrides the common instinct to put white text on a colored button.*
4. **On dark surfaces, orange is safe** (7.75) for text and accents.
5. **Ghost/link text:** use `--chert-ink` with an orange-deep underline, or orange-deep at ≥19px bold **on white only**. For small links on cream, use ink.
6. **Non-text UI** (borders, icons, focus rings) needs 3.0:1. Orange-deep on cream is 2.89 and orange-deep on orange-tint is 2.67 — both fail. **Focus rings and icon glyphs are ink.** Orange is fine as the *fill* behind ink.
7. Never rely on color alone to convey state — pair with an icon or label.

> **Design consequence:** the print identity puts orange type on cream freely. The web system cannot. Where the book cover uses orange text, the UI uses **ink text with orange fills or underlines**. This is the deliberate translation from print to screen — not a compromise.
---

## 4. Typography

### 4.1 Typefaces

| Role | Stack | Where |
|---|---|---|
| **Interface / body (EN)** | `'Inter', system-ui, -apple-system, sans-serif` | Everything |
| **Display (EN)** | `'Playfair Display', Georgia, serif` | Marketing heroes **only** |
| **Arabic (all roles)** | `'IBM Plex Sans Arabic', 'Cairo', sans-serif` | All Arabic text |
| **Mono / data** | `'JetBrains Mono', 'Consolas', monospace` | Code, IDs, metrics, tabular data |

**Playfair Display is restricted.** It appears on marketing hero headlines and nowhere else — never in app UI, never below 40px, never for body text. It is the one moment of print-identity carryover; overusing it dilutes it.

### 4.2 Type scale

| Token | Size | Weight | Line height | Tracking | Use |
|---|---|---|---|---|---|
| `--fs-display` | 56px | 700 | 1.05 | -1.5px | Marketing hero (Playfair) |
| `--fs-h1` | 40px | 800 | 1.1 | -1px | Page title |
| `--fs-h2` | 30px | 700 | 1.15 | -0.5px | Section heading |
| `--fs-h3` | 22px | 700 | 1.25 | 0 | Card title, subsection |
| `--fs-lg` | 18px | 400 | 1.5 | 0 | Lead paragraph |
| `--fs-base` | 16px | 400 | 1.5 | 0 | Body |
| `--fs-sm` | 14px | 500 | 1.45 | 0 | Captions, table cells, nav |
| `--fs-xs` | 13px | 500 | 1.4 | 0 | Helper text, badges |
| `--fs-overline` | 12px | 600 | 1.3 | 3px | Kickers (UPPERCASE) |

**Mobile:** scale `--fs-display` to 36px and `--fs-h1` to 30px. Everything else holds.

### 4.3 Rules

- Body line length: **65–75 characters** max (`max-width: 68ch`).
- Never letter-space lowercase body text. Tracking is for overlines only.
- Headings use tight leading (1.05–1.25); body uses 1.5.
- Only two weights per screen beyond body: pick 700 and 800, don't ladder through 400/500/600/700.

---

## 5. Layout

### 5.1 Spacing

The system is built on an **8px base unit**. Every margin, padding, and gap is a multiple.

```
--space-1: 4px     --space-5: 24px
--space-2: 8px     --space-6: 32px
--space-3: 12px    --space-7: 48px
--space-4: 16px    --space-8: 64px
                   --space-9: 96px
```

4px exists only for tight icon/label pairs. If reaching for a value not on this scale, the layout is wrong.

### 5.2 Grid

| Token | Value |
|---|---|
| Content max-width | `1200px`, centered |
| Wide max-width | `1440px` (dashboards only) |
| Prose max-width | `68ch` |
| Columns | 12, `24px` gap |
| Page gutter | `24px` mobile / `40px` desktop |
| Section padding (Y) | `96px` desktop / `48px` mobile |

### 5.3 Breakpoints

| Name | Width | Card grid |
|---|---|---|
| `sm` | < 640px | 1 column |
| `md` | 640–1023px | 2 columns |
| `lg` | 1024–1439px | 3 columns |
| `xl` | ≥ 1440px | 3 columns, wide container |

**Mobile-first.** Write base styles for `sm`, add complexity upward with `min-width` queries.

### 5.4 Radius, shadow, border

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | `8px` | Buttons, inputs, tags |
| `--radius-md` | `12px` | Icon boxes, dropdowns, small cards |
| `--radius-card` | `16px` | Cards, modals, panels |
| `--radius-pill` | `40px` | Badges, pills, avatars |
| `--border` | `1px solid #ECE0C2` | Default |
| `--shadow-card` | `0 10px 30px -18px rgba(0,0,0,.2)` | Resting card |
| `--shadow-hover` | `0 20px 40px -20px rgba(242,107,51,.4)` | Card hover (orange-tinted) |
| `--shadow-dropdown` | `0 12px 32px -8px rgba(0,0,0,.18)` | Menus, popovers |
| `--shadow-modal` | `0 24px 64px -12px rgba(0,0,0,.3)` | Modals |

The orange-tinted hover shadow is a **signature detail**. Cards lift into warmth, not gray. Do not substitute a neutral shadow.

### 5.5 Elevation

| Level | Surface | Shadow | Example |
|---|---|---|---|
| 0 | `--chert-cream` | none | Page background |
| 1 | `--chert-surface` | `--shadow-card` | Cards |
| 2 | `--chert-surface` | `--shadow-dropdown` | Dropdowns, popovers |
| 3 | `--chert-surface` | `--shadow-modal` | Modals, dialogs |

### 5.6 Z-index

```
--z-base: 0        --z-sticky: 100    --z-dropdown: 200
--z-overlay: 300   --z-modal: 400     --z-toast: 500
```

### 5.7 Marketing page anatomy

Every CHERT marketing site follows this order:

```
┌──────────────────────────────────────────┐
│ HEADER — logo · nav · switcher · CTA     │  sticky, cream
├──────────────────────────────────────────┤
│                                          │
│           HERO (centered)                │  cream
│   pill badge                             │
│   headline (Playfair, 56px)              │
│   lead (18px, 68ch)                      │
│   [Primary CTA] [Outline CTA]            │
│                                          │
├──────────────────────────────────────────┤
│  PRODUCT / FEATURE GRID   3 × cards      │  cream
├──────────────────────────────────────────┤
│  CONTENT SECTION                         │  white
├──────────────────────────────────────────┤
│  CONTENT SECTION                         │  cream
├──────────────────────────────────────────┤
│  CTA BAND                                │  tan
├──────────────────────────────────────────┤
│  FOOTER — all 6 products, cross-linked   │  ink
└──────────────────────────────────────────┘
```

Sections **alternate cream and white**. Never place two white sections adjacent.

### 5.8 App shell anatomy

For product UIs (ERP, BI, Fleet, POS, Mail):

```
┌────────┬─────────────────────────────────┐
│        │ TOPBAR — breadcrumb · search ·  │
│ SIDE   │          switcher · avatar      │
│ BAR    ├─────────────────────────────────┤
│ tan    │                                 │
│ 250px  │  CONTENT — cream                │
│        │  cards / tables / charts        │
│ nav    │                                 │
│        │                                 │
│ [CTA]  │                                 │
└────────┴─────────────────────────────────┘
```

- Sidebar: `--chert-tan`, 250px, collapses to icons at `md`, drawer at `sm`.
- Active nav item: ink pill, cream text.
- Topbar: white, 64px, `--border` bottom.

---

## 6. Components

Every component below is **mandatory and shared**. Build once, use in all six products.

### 6.1 Buttons

| Variant | Spec |
|---|---|
| **Primary** | bg `--chert-orange`, **text `--chert-ink` 700** (7.29:1), radius 8px, padding `11px 22px` |
| Primary :hover | bg `--chert-orange-deep`, text ink, `translateY(-1px)` |
| Primary :active | bg `--chert-orange-deep`, `translateY(0)` |
| **Secondary** | transparent, `1.5px solid --chert-ink`, text ink 700 |
| Secondary :hover | bg `--chert-ink`, text cream (16.64:1) |
| **Ghost** | transparent, no border, **text `--chert-ink` 700**, orange-deep underline on hover |
| **Danger** | bg `--chert-error`, **text `#FFF` 700 at ≥19px bold** (3.76:1, large-text AA) — or ink for small |
| **On dark** | bg `--chert-orange`, text `--chert-ink` 700 |
| :disabled | `opacity: .45`, `cursor: not-allowed`, no hover |
| :focus-visible | `2px solid --chert-ink`, `outline-offset: 2px` |

> **Why ink and not white on the primary button?** White on orange is 2.39:1 and fails AA. Ink on orange is 7.29:1 and passes at any size. The CHERT primary button has **dark text on an orange fill** — this is a defining characteristic of the system, not an oversight. It also matches the print identity, where black type sits on orange fields.

**Sizes:** `sm` 8×16 / 14px · `md` 11×22 / 14px (default) · `lg` 14×28 / 16px

**The one-primary rule:** exactly **one** primary orange button per view. Pair it with a secondary or ghost. Two orange buttons side by side means neither is primary.

### 6.2 Cards

| Property | Value |
|---|---|
| Background | `--chert-surface` |
| Border | `--border` |
| Radius | `--radius-card` (16px) |
| Padding | `28px` |
| Shadow | `--shadow-card` |
| Hover | `translateY(-4px)`, `--shadow-hover`, 150ms |

**Card icon box:** 46×46, `--radius-md`, bg `--chert-orange-tint`, starburst in `--chert-ink` at 26px.
*(Orange-deep on orange-tint is 2.67:1 and fails the 3:1 non-text minimum — the starburst is ink.)*

**Anatomy:** icon box → 16px → title (h3) → 8px → description (`--fs-sm`, muted) → 14px → link (ghost style).

### 6.3 Callouts

Left border 4px + tinted fill + 16px padding + `--radius-sm`.

| Type | Border | Fill |
|---|---|---|
| Note | `--chert-orange-deep` | `--chert-orange-tint` |
| Success | `--chert-success` | `#E7F8F2` |
| Warning | `--chert-warning` | `#FEF4E3` |
| Error | `--chert-error` | `#FDECEC` |
| Info | `--chert-info` | `#EAF1FE` |

### 6.4 Forms

| Property | Value |
|---|---|
| Height | `44px` (48px touch targets on mobile) |
| Padding | `10px 14px` |
| Background | `--chert-surface` |
| Border | `--border`, `--radius-sm` |
| Font | `--fs-base` |
| Placeholder | `--chert-muted` |
| :focus | border `--chert-orange`, `box-shadow: 0 0 0 3px rgba(255,134,81,.25)` |
| :disabled | bg `--chert-surface-alt`, muted text |
| Error | border `--chert-error` + 13px error helper below |
| Label | `--fs-sm` 600 ink, 6px above |
| Helper | `--fs-xs` muted, 6px below |

**Field spacing:** 20px between fields, 32px between field groups.

Checkbox/radio: 18px, `--radius-sm` (checkbox) / circle (radio), checked = orange fill, white glyph.
Toggle: 44×24 pill, off = `--chert-border`, on = `--chert-orange`, white knob, 150ms.

### 6.5 Navigation

**Header (marketing):**
- Sticky, `--chert-cream`, 72px tall, `--z-sticky`
- On scroll >8px: add `--border` bottom + `0 2px 12px -6px rgba(0,0,0,.1)`
- Links: `--fs-sm` 600, ink at 85% opacity → 100% ink + 2px orange underline on hover/active (underline is decoration, so orange is safe here)
- Right side: cross-product switcher, then ghost "Sign in", then primary CTA

**Dropdown:**
- White, `--radius-md`, `--shadow-dropdown`, 8px padding
- Items: 8px 12px, `--radius-sm`, hover = `--chert-orange-tint` bg + **ink** text
- Enter: fade + 4px rise, 120ms

**Mobile nav:**
- Hamburger → full-width cream drawer, slides from inline-end
- Links stack, 18px, 16px vertical padding (48px touch target)
- Close on Esc, click-outside, and route change. Trap focus while open.

**Sidebar (app):**
- `--chert-tan`, 250px, 32px 26px padding
- Items: 10px 14px, `--radius-sm`, ink at 80%
- Active: bg `--chert-ink`, text `--chert-cream`, full opacity
- Bottom-pinned primary CTA

### 6.6 Cross-product switcher — required

**Every CHERT product must include this.** It is the mechanism that makes six sites feel like one system.

- Trigger: starburst icon + current product name + chevron, in the header
- Panel: white, `--radius-md`, `--shadow-dropdown`, 320px, 2-column grid of all six products
- Each entry: starburst icon box + product name + one-line description
- Current product: `--chert-orange-tint` bg, **ink** text, orange left-border marker, not clickable
 

### 6.7 Data display

**Table:**
- Header: `--chert-ink` bg, white text, `--fs-sm` 700, 12px 16px padding
- Rows: zebra `--chert-surface` / `--chert-surface-alt`, 14px 16px
- Row hover: `--chert-orange-tint`
- Numeric columns: right-aligned (LTR), mono font
- Border: `--border` between rows

**Badge:** `--radius-pill`, 4px 12px, `--fs-xs` 600, tinted bg + matching deep text.
**Tag:** `--chert-tan` bg, ink text, `--radius-sm`, 3px 8px, `--fs-xs`.
**Avatar:** circle, `--chert-tan` bg, ink initials 600.
**Divider:** 1px `--chert-border`, or centered 24px starburst with hairlines either side for section breaks.

**Charts (BI/Fleet):** categorical sequence in order —
`#FF8651` → `#D2B082` → `#1A1A18` → `#F26B33` → `#A89E8D` → `#6B6B66`.
Grid lines `--chert-border`. Never use rainbow or default library palettes.

### 6.8 Feedback

**Toast:** bottom-inline-end, white, `--radius-md`, `--shadow-dropdown`, 4px left border in status color, auto-dismiss 5s, stack upward.
**Modal:** white, `--radius-card`, `--shadow-modal`, max 560px, backdrop `rgba(26,26,24,.5)`. Trap focus, close on Esc.
**Loading:** rotating starburst, `--chert-orange`, 1.2s linear infinite.
**Skeleton:** `--chert-surface-alt` blocks, subtle shimmer, matching final radius.
**Empty state:** centered starburst (48px, `--chert-tan`) + heading + one-line explanation + primary action. **Always offer the next action.**

### 6.9 Motion

| Token | Value | Use |
|---|---|---|
| `--ease` | `cubic-bezier(.4,0,.2,1)` | Default |
| `--dur-fast` | `120ms` | Hover, focus |
| `--dur-base` | `150ms` | Cards, buttons |
| `--dur-slow` | `240ms` | Drawers, modals |

Animate `transform` and `opacity` only. Never animate `width`, `height`, `top`, or `left`.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```
---

## 7. Bilingual & RTL (Arabic)

Every CHERT product ships **English (LTR) and Arabic (RTL) from one codebase**. Never fork the design per language.

### 7.1 The core technique

Use **CSS logical properties** everywhere. Mirroring then happens automatically when `dir` flips — no RTL stylesheet, no duplicated rules.

| ❌ Never use | ✅ Always use |
|---|---|
| `margin-left` | `margin-inline-start` |
| `margin-right` | `margin-inline-end` |
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `left` / `right` | `inset-inline-start` / `inset-inline-end` |
| `text-align: left` | `text-align: start` |
| `border-left` | `border-inline-start` |
| `margin-top/bottom` | `margin-block-start/end` |

Set direction on the root:

```html
<html lang="en" dir="ltr">   <!-- English -->
<html lang="ar" dir="rtl">   <!-- Arabic -->
```

### 7.2 What mirrors and what doesn't

| ✅ Mirrors | ❌ Never mirrors |
|---|---|
| Header logo → top-right | The arrowhead logo itself |
| Nav flow, sidebar → right edge | The starburst |
| Text alignment → right | Numerals and digits |
| Arrows, chevrons, back/next | Media controls (play stays ▶) |
| Progress bars, breadcrumbs | Charts with a time axis |
| Table column order | Code blocks |
| Card icon placement | Clock icons |

**Flipping directional icons:**

```css
[dir="rtl"] .icon-directional { transform: scaleX(-1); }
```

Apply only to arrows/chevrons — never to the logo, starburst, or brand imagery.

### 7.3 Bidi isolation — required

Numbers, dates, domains, emails, IDs, and code must stay LTR inside Arabic text, or they will render scrambled.

```html
<p>رقم الطلب <span dir="ltr" style="unicode-bidi:isolate">INV-2024-0042</span> جاهز</p>
```

```css
.ltr-content {
  direction: ltr;
  unicode-bidi: isolate;
  display: inline-block;
}
```

Apply `.ltr-content` to: order/invoice IDs, phone numbers, emails, URLs, currency amounts, timestamps, version numbers, code.

### 7.4 Arabic typography

| Property | Value | Why |
|---|---|---|
| Font | `'IBM Plex Sans Arabic', 'Cairo', sans-serif` | Full weight range, screen-tuned |
| Body size | **+1px** vs English (17px vs 16px) | Arabic reads optically smaller |
| Line height | **1.7** (vs 1.5 EN) | Ascenders/descenders need room |
| Letter-spacing | **`normal` — never adjust** | Breaks letter joining |
| Italics | **Never** | No true italic in Arabic; synthesized slant is wrong |
| Text-transform | **Never** | Arabic has no letter case |
| Alignment | `start` (= right in RTL) | — |

```css
[lang="ar"] {
  font-family: 'IBM Plex Sans Arabic', 'Cairo', sans-serif;
  font-size: 17px;
  line-height: 1.7;
  letter-spacing: normal;
}
[lang="ar"] em, [lang="ar"] i { font-style: normal; font-weight: 700; }
[lang="ar"] .overline { letter-spacing: normal; text-transform: none; }
```

**Playfair Display has no Arabic.** In Arabic, the marketing hero uses IBM Plex Sans Arabic at 700 — the display serif is an English-only device. Accept that the Arabic hero reads differently; do not substitute a mismatched serif.

### 7.5 Language switcher

- In the header, next to the product switcher.
- Labeled in the **target** language: shows `العربية` when in English, `English` when in Arabic.
- Persists choice (`localStorage` + `Accept-Language` fallback).
- Never uses a flag icon — language ≠ country.

### 7.6 RTL checklist

- [ ] `dir` and `lang` set on `<html>` and flip together
- [ ] Zero physical properties (`left`/`right`/`margin-left`…) in the codebase
- [ ] Logo and starburst not mirrored
- [ ] Arrows/chevrons mirrored
- [ ] Numbers, IDs, emails bidi-isolated
- [ ] Arabic font, +1px, 1.7 line height applied
- [ ] No italics or letter-spacing on Arabic
- [ ] Sidebar and drawers slide from the correct edge
- [ ] Both directions tested at every breakpoint

---

## 8. Accessibility

**WCAG 2.1 AA is the floor, not a goal.** Every CHERT product must meet it.

### 8.1 Non-negotiables

- **Contrast:** 4.5:1 body text, 3:1 large text and UI boundaries. See §3.6 — orange text on cream is the trap.
- **Focus:** every interactive element has a visible `:focus-visible` ring — `2px solid --chert-ink`, `outline-offset: 2px` (ink clears 3:1 on every CHERT surface; orange does not). **Never `outline: none` without a replacement.**
- **Touch targets:** ≥44×44px.
- **Keyboard:** every action reachable and operable. Logical tab order. Focus trapped in modals/drawers, restored on close.
- **Semantics:** real `<button>`, `<nav>`, `<main>`, `<h1>`–`<h6>` in order. Never a clickable `<div>`.
- **Labels:** every input has a `<label>`. Icon-only buttons get `aria-label`.
- **Images:** meaningful `alt`; decorative marks get `aria-hidden="true"`.
- **State:** never color alone — pair with icon or text.
- **Motion:** honor `prefers-reduced-motion`.
- **Skip link:** "Skip to content" as the first focusable element.

### 8.2 Component ARIA

| Component | Requirements |
|---|---|
| Modal | `role="dialog"` `aria-modal="true"` `aria-labelledby`, focus trap, Esc closes, focus restored |
| Dropdown | `aria-expanded`, `aria-haspopup`, arrow-key navigation, Esc closes |
| Toast | `role="status"` (info) / `role="alert"` (error) |
| Tabs | `role="tablist"`/`tab`/`tabpanel`, `aria-selected`, arrow keys |
| Toggle | `role="switch"` `aria-checked` |
| Table | `<th scope>`, `<caption>` |
| Loading | `aria-busy="true"`, `aria-live="polite"` |

---

## 9. Design tokens (`chert-tokens.css`)

**Copy this file verbatim into every CHERT project.** It is the contract.

```css
/* ============================================================
   CHERT Design Tokens v1.0
   Single source of truth. Do not edit per-project.
   ============================================================ */

:root {
  /* ---- Brand ---- */
  --chert-orange:       #FF8651;
  --chert-orange-deep:  #F26B33;
  --chert-tan:          #D2B082;
  --chert-cream:        #FFFAE4;
  --chert-ink:          #1A1A18;

  /* ---- Extended ---- */
  --chert-surface:      #FFFFFF;
  --chert-surface-alt:  #FBF7EC;
  --chert-border:       #ECE0C2;
  --chert-border-strong:#D9C9A4;
  --chert-muted:        #6B6B66;
  --chert-orange-tint:  #FDEEE4;

  /* ---- Functional ---- */
  --chert-success:      #10B981;
  --chert-success-tint: #E7F8F2;
  --chert-warning:      #F59E0B;
  --chert-warning-tint: #FEF4E3;
  --chert-error:        #EF4444;
  --chert-error-tint:   #FDECEC;
  --chert-info:         #3B82F6;
  --chert-info-tint:    #EAF1FE;

  /* ---- Dark surfaces ---- */
  --chert-dark:         #151311;
  --chert-dark-surface: #1B1815;
  --chert-dark-border:  #26221D;
  --chert-dark-text:    #F3EDE0;
  --chert-dark-muted:   #A89E8D;

  /* ---- Type ---- */
  --font-ui:      'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Playfair Display', Georgia, serif;
  --font-ar:      'IBM Plex Sans Arabic', 'Cairo', sans-serif;
  --font-mono:    'JetBrains Mono', 'Consolas', monospace;

  --fs-display:  56px;
  --fs-h1:       40px;
  --fs-h2:       30px;
  --fs-h3:       22px;
  --fs-lg:       18px;
  --fs-base:     16px;
  --fs-sm:       14px;
  --fs-xs:       13px;
  --fs-overline: 12px;

  --lh-tight: 1.1;
  --lh-snug:  1.25;
  --lh-base:  1.5;
  --lh-ar:    1.7;

  /* ---- Spacing (8px base) ---- */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 24px;  --space-6: 32px;
  --space-7: 48px;  --space-8: 64px;  --space-9: 96px;

  /* ---- Layout ---- */
  --maxw:       1200px;
  --maxw-wide:  1440px;
  --maxw-prose: 68ch;
  --gutter:     24px;
  --sidebar-w:  250px;
  --header-h:   72px;

  /* ---- Radius ---- */
  --radius-sm:   8px;
  --radius-md:   12px;
  --radius-card: 16px;
  --radius-pill: 40px;

  /* ---- Shadow ---- */
  --shadow-card:     0 10px 30px -18px rgba(0,0,0,.2);
  --shadow-hover:    0 20px 40px -20px rgba(242,107,51,.4);
  --shadow-dropdown: 0 12px 32px -8px rgba(0,0,0,.18);
  --shadow-modal:    0 24px 64px -12px rgba(0,0,0,.3);

  /* ---- Motion ---- */
  --ease:      cubic-bezier(.4,0,.2,1);
  --dur-fast:  120ms;
  --dur-base:  150ms;
  --dur-slow:  240ms;

  /* ---- Z-index ---- */
  --z-base: 0;      --z-sticky: 100;  --z-dropdown: 200;
  --z-overlay: 300; --z-modal: 400;   --z-toast: 500;
}

@media (min-width: 1024px) { :root { --gutter: 40px; } }
@media (max-width: 639px) {
  :root { --fs-display: 36px; --fs-h1: 30px; --fs-h2: 24px; --header-h: 64px; }
}

/* ---- Base ---- */
*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--chert-cream);
  color: var(--chert-ink);
  font-family: var(--font-ui);
  font-size: var(--fs-base);
  line-height: var(--lh-base);
  -webkit-font-smoothing: antialiased;
}

[lang="ar"] {
  font-family: var(--font-ar);
  font-size: 17px;
  line-height: var(--lh-ar);
  letter-spacing: normal;
}
[lang="ar"] em, [lang="ar"] i { font-style: normal; font-weight: 700; }
[dir="rtl"] .icon-directional { transform: scaleX(-1); }

.ltr-content { direction: ltr; unicode-bidi: isolate; display: inline-block; }

:focus-visible {
  outline: 2px solid var(--chert-ink);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### 9.1 Tailwind mapping

```js
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        chert: {
          orange: '#FF8651', 'orange-deep': '#F26B33',
          tan: '#D2B082', cream: '#FFFAE4', ink: '#1A1A18',
          surface: '#FFFFFF', 'surface-alt': '#FBF7EC',
          border: '#ECE0C2', muted: '#6B6B66', tint: '#FDEEE4',
          dark: '#151311', 'dark-surface': '#1B1815',
        },
      },
      fontFamily: {
        ui: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Playfair Display', 'Georgia', 'serif'],
        ar: ['IBM Plex Sans Arabic', 'Cairo', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      borderRadius: { sm: '8px', md: '12px', card: '16px', pill: '40px' },
      boxShadow: {
        card: '0 10px 30px -18px rgba(0,0,0,.2)',
        hover: '0 20px 40px -20px rgba(242,107,51,.4)',
        dropdown: '0 12px 32px -8px rgba(0,0,0,.18)',
        modal: '0 24px 64px -12px rgba(0,0,0,.3)',
      },
      maxWidth: { content: '1200px', wide: '1440px', prose: '68ch' },
    },
  },
  plugins: [require('tailwindcss-logical')], // enforces RTL-safe utilities
};
```

---

## 10. Component reference implementation

```css
/* ---- Buttons ---- */
.btn {
  font-family: inherit;
  font-size: var(--fs-sm);
  font-weight: 700;
  padding: 11px 22px;
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
  transition: background var(--dur-base) var(--ease),
              transform var(--dur-base) var(--ease);
}
/* Primary: INK text on orange (7.29:1). White on orange fails AA (2.39:1). */
.btn--primary   { background: var(--chert-orange); color: var(--chert-ink); }
.btn--primary:hover { background: var(--chert-orange-deep); transform: translateY(-1px); }
.btn--secondary { background: transparent; border: 1.5px solid var(--chert-ink); color: var(--chert-ink); }
.btn--secondary:hover { background: var(--chert-ink); color: var(--chert-cream); }
/* Ghost: ink text — orange-deep on cream fails AA (2.89:1). */
.btn--ghost     { background: transparent; color: var(--chert-ink); padding-inline: 0; }
.btn--ghost:hover { text-decoration: underline; text-decoration-color: var(--chert-orange-deep); text-underline-offset: 3px; }
.btn--danger    { background: var(--chert-error); color: #fff; font-size: var(--fs-base); }
.btn:disabled   { opacity: .45; cursor: not-allowed; transform: none; }
.btn--sm { padding: 8px 16px; }
.btn--lg { padding: 14px 28px; font-size: var(--fs-base); }

/* ---- Card ---- */
.card {
  background: var(--chert-surface);
  border: 1px solid var(--chert-border);
  border-radius: var(--radius-card);
  padding: 28px;
  box-shadow: var(--shadow-card);
  transition: transform var(--dur-base) var(--ease),
              box-shadow var(--dur-base) var(--ease);
}
.card:hover { transform: translateY(-4px); box-shadow: var(--shadow-hover); }

.card__icon {
  width: 46px; height: 46px;
  display: grid; place-items: center;
  border-radius: var(--radius-md);
  background: var(--chert-orange-tint);
  color: var(--chert-ink);
  margin-block-end: var(--space-4);
}
.card__title { font-size: var(--fs-h3); font-weight: 700; margin: 0 0 var(--space-2); }
.card__desc  { font-size: var(--fs-sm); color: var(--chert-muted); margin: 0 0 14px; }
.card__link  { font-size: var(--fs-sm); font-weight: 700; color: var(--chert-ink);
               text-decoration: underline; text-decoration-color: var(--chert-orange);
               text-underline-offset: 3px; }

/* ---- Input ---- */
.input {
  width: 100%;
  height: 44px;
  padding: 10px 14px;
  font-family: inherit;
  font-size: var(--fs-base);
  background: var(--chert-surface);
  border: 1px solid var(--chert-border);
  border-radius: var(--radius-sm);
  color: var(--chert-ink);
  transition: border-color var(--dur-fast) var(--ease),
              box-shadow var(--dur-fast) var(--ease);
}
.input::placeholder { color: var(--chert-muted); }
.input:focus {
  outline: none;
  border-color: var(--chert-orange);
  box-shadow: 0 0 0 3px rgba(255,134,81,.25);
}
.input--error { border-color: var(--chert-error); }
.label { display: block; font-size: var(--fs-sm); font-weight: 600; margin-block-end: 6px; }
.helper { font-size: var(--fs-xs); color: var(--chert-muted); margin-block-start: 6px; }

/* ---- Callout ---- */
.callout {
  border-inline-start: 4px solid var(--chert-orange-deep);
  background: var(--chert-orange-tint);
  padding: var(--space-4);
  border-radius: var(--radius-sm);
}
.callout--success { border-color: var(--chert-success); background: var(--chert-success-tint); }
.callout--warning { border-color: var(--chert-warning); background: var(--chert-warning-tint); }
.callout--error   { border-color: var(--chert-error);   background: var(--chert-error-tint); }
.callout--info    { border-color: var(--chert-info);    background: var(--chert-info-tint); }

/* ---- Layout ---- */
.container { max-width: var(--maxw); margin-inline: auto; padding-inline: var(--gutter); }
.section   { padding-block: var(--space-9); }
.section--alt { background: var(--chert-surface); }

.grid-cards { display: grid; grid-template-columns: 1fr; gap: var(--space-5); }
@media (min-width: 640px)  { .grid-cards { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .grid-cards { grid-template-columns: repeat(3, 1fr); } }

/* ---- Header ---- */
.header {
  position: sticky; inset-block-start: 0; z-index: var(--z-sticky);
  height: var(--header-h);
  display: flex; align-items: center; justify-content: space-between;
  padding-inline: var(--gutter);
  background: var(--chert-cream);
  transition: box-shadow var(--dur-base) var(--ease);
}
.header--scrolled {
  border-block-end: 1px solid var(--chert-border);
  box-shadow: 0 2px 12px -6px rgba(0,0,0,.1);
}

/* ---- Starburst loader ---- */
.chert-star { width: 26px; height: 26px; }
.loader { animation: chert-spin 1.2s linear infinite; color: var(--chert-orange); }
@keyframes chert-spin { to { transform: rotate(360deg); } }
```

---

## 11. Build checklist

Run this before shipping **any** CHERT site or system.

### Identity
- [ ] Arrowhead logo in header, correct size and clear space
- [ ] Starburst used for icons, loaders, dividers
- [ ] No per-product logo or per-product color introduced
- [ ] Product name written as `chertkearninghub` / `CHERT Learning Hub`, never `Chert Learning Hub`

### Tokens
- [ ] `chert-tokens.css` imported unmodified
- [ ] Zero hardcoded hex values in the codebase
- [ ] All spacing on the 8px scale
- [ ] Radius, shadow, motion all from tokens

### Color
- [ ] 60-30-10 respected — orange is a signal, not a surface
- [ ] **No orange text on cream anywhere**
- [ ] Primary buttons use **ink** text on orange, not white
- [ ] No orange-deep body text on cream (fails AA at 2.89)
- [ ] Functional colors used only for status

### Type
- [ ] Playfair only in marketing hero, ≥40px
- [ ] Body ≤68ch line length
- [ ] Type scale followed exactly

### Layout
- [ ] Sections alternate cream / white
- [ ] Card grid 3 / 2 / 1 across lg / md / sm
- [ ] Container max-width 1200px

### Components
- [ ] Exactly one primary orange button per view
- [ ] Cards use the orange-tinted hover shadow
- [ ] **Cross-product switcher present in header**
- [ ] Unified footer with all six products
- [ ] Empty states offer a next action

### Bilingual
- [ ] EN and AR both render from one codebase
- [ ] Zero physical CSS properties — logical only
- [ ] Logo and starburst not mirrored; arrows mirrored
- [ ] Numbers, IDs, emails bidi-isolated
- [ ] Arabic at 17px / 1.7, no italics, no letter-spacing

### Accessibility
- [ ] Contrast AA verified (esp. anything orange)
- [ ] Visible focus ring on every interactive element
- [ ] Full keyboard operability; focus trapped in modals
- [ ] Touch targets ≥44px
- [ ] Semantic HTML; no clickable divs
- [ ] `prefers-reduced-motion` honored
- [ ] Skip link present

### Voice
- [ ] Active voice, sentence case
- [ ] Buttons name their action; action name persists into the toast
- [ ] Errors say what happened and how to fix it

---

## 12. Quick reference

```
COLOR    orange #FF8651 · deep #F26B33 · tan #D2B082 · cream #FFFAE4 · ink #1A1A18
TYPE     Inter (UI) · Playfair (hero only) · IBM Plex Sans Arabic (AR) · JetBrains Mono
SPACE    8px base — 4 8 12 16 24 32 48 64 96
RADIUS   8 (button) · 12 (icon) · 16 (card) · 40 (pill)
GRID     1200px · 12 col · 24px gap · 3/2/1 cards
SHADOW   card 0 10px 30px -18px rgba(0,0,0,.2) · hover orange-tinted
MOTION   150ms cubic-bezier(.4,0,.2,1) · transform + opacity only

THE THREE RULES THAT BREAK THE SYSTEM MOST OFTEN
1. Orange OR orange-deep text on cream — both fail AA. Use ink.
2. More than one primary orange button per view.
3. Physical CSS properties (left/right) — breaks Arabic.
```

---

*CHERT Systems — Identity & Digital Design Guide · v1.0*
*Applies to: chertlearninghub 
