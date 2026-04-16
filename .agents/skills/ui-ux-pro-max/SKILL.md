---
name: ui-ux-pro-max
description: Activate when building UI/UX — landing pages, dashboards, web apps, or any visual interface. Generates data-driven design systems (colors, typography, styles, patterns) from a 240KB curated database. Use BEFORE writing any frontend code.
---

# UI/UX Pro Max Skill

> **Design decisions should come from data, not vibes.** This skill searches a curated database of 50+ styles, 97 color palettes, 57 font pairings, and 99 UX guidelines to generate a complete design system BEFORE any code is written.

## When to Activate

- Building a landing page, dashboard, or web app
- User asks for UI/UX design decisions (colors, fonts, layout)
- Starting any frontend implementation
- Reviewing or improving an existing UI

## Stream Coding Integration

```
🎯 STRATEGY: "What should this look like?"
   └─ /ui-ux-pro-max → generates design system
   └─ Output: design constraints for the spec

📋 SPEC: Design system = implementation spec sections
   └─ Colors, fonts, spacing, anti-patterns → spec tables
   └─ Pre-delivery checklist → test cases

⚡ BUILD: Code follows the design spec
   └─ No guessing. Every visual choice traces to the design system.
```

## Usage

### 1. Generate a Design System (ALWAYS START HERE)

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system -p "Project Name"
```

**Example:**
```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "SaaS dashboard fintech professional" --design-system -p "FinTrack Pro"
```

Output includes: pattern, style, colors, typography, key effects, anti-patterns, and pre-delivery checklist.

### 2. Persist the Design System (for multi-session projects)

```bash
# Save as MASTER.md (global source of truth)
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name"

# With page-specific override
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

Creates `design-system/MASTER.md` and optional `design-system/pages/<page>.md` overrides.

### 3. Domain-Specific Searches (supplement the design system)

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

| Need | Domain | Example |
|------|--------|---------|
| More style options | `style` | `"glassmorphism dark"` |
| Chart recommendations | `chart` | `"real-time dashboard"` |
| UX best practices | `ux` | `"animation accessibility"` |
| Alternative fonts | `typography` | `"elegant luxury"` |
| Landing structure | `landing` | `"hero social-proof"` |
| Color palettes | `color` | `"fintech crypto"` |
| Product patterns | `product` | `"SaaS B2B"` |
| Icon sets | `icons` | `"minimal outline"` |

### 4. Stack-Specific Guidelines

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<keyword>" --stack <stack>
```

Available stacks: `html-tailwind`, `react`, `nextjs`, `vue`, `nuxtjs`, `nuxt-ui`, `svelte`, `swiftui`, `react-native`, `flutter`, `shadcn`, `jetpack-compose`

### 5. JSON Output (for programmatic use)

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain style --json
```

## Pre-Delivery Checklist

Before delivering any UI code, verify:

| # | Check | Rule |
|---|-------|------|
| 1 | **No emoji icons** | Use SVG (Heroicons, Lucide, Simple Icons) |
| 2 | **cursor-pointer** | On ALL clickable/hoverable elements |
| 3 | **Smooth transitions** | 150-300ms, ease-out for enter, ease-in for exit |
| 4 | **Contrast** | Light mode text ≥ 4.5:1 ratio |
| 5 | **Focus states** | Visible for keyboard navigation |
| 6 | **Reduced motion** | `prefers-reduced-motion` respected |
| 7 | **Responsive** | Tested at 375px, 768px, 1024px, 1440px |
| 8 | **No layout shift** | Hover states don't move elements |

## Database Contents

| Data File | Records | Coverage |
|-----------|---------|----------|
| `styles.csv` | 50+ UI styles | Glassmorphism, brutalism, neumorphism, etc. |
| `colors.csv` | 97 palettes | By industry and product type |
| `typography.csv` | 57 font pairings | Google Fonts with mood/use-case |
| `products.csv` | Product patterns | SaaS, e-commerce, portfolio, etc. |
| `landing.csv` | Landing structures | Hero, CTA, social-proof patterns |
| `ux-guidelines.csv` | 99 guidelines | Animation, a11y, z-index, loading |
| `charts.csv` | 25 chart types | By data visualization need |
| `ui-reasoning.csv` | Reasoning rules | Why certain combos work/fail |
| `stacks/*.csv` | 12 stacks | Framework-specific best practices |

---

**Remember**: A design system is a spec. If you skip generating one, you're vibe-coding the visuals.
