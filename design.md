# RecoveryOS — design.md

## 1. Purpose

This document is the visual and UX source of truth for RecoveryOS.

The coding agent must use this design system for every frontend page and component. Do not replace it with a generic SaaS dashboard, default shadcn styling, blue/purple AI gradients, glassmorphism, neon colors, excessive rounded cards, or dense enterprise UI.

The product is a serious revenue-recovery intelligence platform, but its visual identity is:

**Editorial. Timeless. Warm. Refined.**

The interface should feel like a premium financial/editorial product rather than a conventional AI dashboard.

---

# 2. Frontend Design Stack

The design system is implemented with:

- React
- Vite
- Tailwind CSS
- Recharts
- CSS custom properties/design tokens
- Playfair Display
- Source Sans 3
- IBM Plex Mono

Do not introduce another UI framework unless explicitly requested.

Do not introduce a second styling system.

Tailwind + centralized CSS variables are the styling foundation.

---

# 3. Design Philosophy

## Core principle

**Typographic elegance through classical restraint.**

The visual system uses:
- strong serif typography;
- warm ivory surfaces;
- rich black text;
- warm gray secondary text;
- one restrained burnished-gold accent;
- thin editorial rule lines;
- generous whitespace;
- subtle depth;
- restrained motion.

The interface should communicate:
- trust;
- intelligence;
- financial seriousness;
- clarity;
- control;
- sophistication.

It should NOT communicate:
- gaming;
- crypto;
- generic AI;
- aggressive growth marketing;
- flashy automation;
- cyberpunk aesthetics.

---

# 4. Color Tokens

Create centralized CSS variables. Do not scatter raw colors throughout JSX.

```css
:root {
  --background: #FAFAF8;
  --foreground: #1A1A1A;

  --muted: #F5F3F0;
  --muted-foreground: #6B6B6B;

  --accent: #B8860B;
  --accent-secondary: #D4A84B;
  --accent-foreground: #FFFFFF;

  --border: #E8E4DF;
  --card: #FFFFFF;
  --ring: #B8860B;
}
```

Additional derived tokens may be created only when needed:

```css
--accent-muted: rgba(184, 134, 11, 0.06);
--shadow-sm: 0 1px 2px rgba(26,26,26,0.04);
--shadow-md: 0 4px 12px rgba(26,26,26,0.06);
--shadow-lg: 0 8px 24px rgba(26,26,26,0.08);
```

### Color rules

- Ivory is the primary page background.
- White is reserved for cards/surfaces.
- Rich black is primary text.
- Warm gray is secondary text.
- Gold is the only strong accent.
- Gold must be used sparingly.
- Do not introduce blue, purple, cyan, green, red, orange, or gradients as primary brand colors.

### Semantic statuses

RecoveryOS needs operational statuses. Preserve the editorial palette while still making states understandable.

Use restrained semantic treatment:
- success: muted green text/background;
- warning: warm gold treatment;
- danger: muted red text/background;
- neutral: warm gray.

Semantic colors must not overpower the main gold/ivory visual identity.

---

# 5. Typography

## Fonts

### Headlines

```css
font-family: "Playfair Display", Georgia, serif;
```

Use for:
- h1;
- h2;
- h3;
- important metric numbers;
- major display values;
- featured quotes.

### Body/UI

```css
font-family: "Source Sans 3", system-ui, sans-serif;
```

Use for:
- body copy;
- navigation;
- buttons;
- forms;
- descriptions;
- table content;
- dashboard operational content.

### Labels/technical metadata

```css
font-family: "IBM Plex Mono", monospace;
```

Use for:
- section labels;
- status metadata;
- timestamps;
- model versions;
- policy versions;
- technical identifiers;
- small uppercase labels.

---

# 6. Typography Scale

| Element | Desktop | Mobile | Font |
|---|---:|---:|---|
| Hero/display | 4.5rem | 2.5rem | Playfair Display |
| Section heading | 2.5rem | 2rem | Playfair Display |
| Card heading | 1.25rem | 1.125rem | Playfair Display |
| Metric number | 3rem–4rem | 2rem–2.5rem | Playfair Display |
| Body | 1rem–1.125rem | 1rem | Source Sans 3 |
| Navigation | 0.875rem | 0.875rem | Source Sans 3 |
| Section label | 0.75rem | 0.6875rem | IBM Plex Mono |

Body line-height:

```text
1.75
```

Heading line-height:

```text
1.1–1.2
```

---

# 7. Small-Caps / Label Pattern

Use this consistently:

```css
.small-caps {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
```

Examples:

```text
RECOVERY COMMAND CENTER
AI DECISION
REVENUE AT RISK
POLICY
MODEL VERSION
AUDIT TRAIL
```

These labels should feel like editorial metadata, not large UI headings.

---

# 8. Layout System

## Page background

```text
#FAFAF8
```

## Container

Prefer:

```text
max-width: 64rem
```

For dashboard pages, a wider container may be used when tables/charts require it, but avoid full-width clutter.

## Section spacing

Desktop:

```text
py-32 to py-44
```

Dashboard sections can be denser where operational usability requires it, but still use generous whitespace.

## Grid gaps

Prefer:

```text
gap-8
gap-10
gap-12
```

Avoid cramped grids.

---

# 9. Editorial Rule System

Thin rules are a signature visual element.

Use:

```css
border-color: var(--border);
border-width: 1px;
```

Use rules for:
- section separators;
- table separators;
- card top borders;
- metadata divisions;
- dashboard grouping.

Accent rules may use:

```css
border-color: var(--accent);
```

Do not use thick decorative borders.

---

# 10. Cards

## Standard card

```text
background: var(--card)
border: 1px solid var(--border)
border-radius: 8px
box-shadow: var(--shadow-sm)
```

Padding:

```text
p-8 to p-10
```

## Featured card

Use:
- subtle accent-tinted background;
- 2px gold top border;
- slightly stronger shadow.

Do not make every card featured.

## Hover

Only interactive cards may have hover treatment.

Use:
- slightly stronger shadow;
- subtle background tint;
- border shift.

Do not use aggressive card movement.

---

# 11. Dashboard Visual Hierarchy

RecoveryOS is a decision system, so the dashboard must prioritize business outcomes.

Recommended hierarchy:

```text
Page title
↓
Context / date / system state
↓
Key financial metrics
↓
Recovery queue
↓
AI decision details
↓
Charts / experiment results
↓
Audit and operational details
```

The most important number on a page should be visually obvious without making the page flashy.

---

# 12. Command Center

The main dashboard should communicate:

### Primary metrics

- Revenue at Risk
- Revenue Recovered
- Baseline Recovery
- Incremental Recovery
- Net Incremental Recovery

Use large Playfair Display numbers.

Example hierarchy:

```text
NET INCREMENTAL RECOVERY
₹1,24,800
+18.4% vs baseline
```

Supporting labels use IBM Plex Mono.

---

# 13. Recovery Queue

The queue is an operational work surface.

Columns:

```text
CASE
AMOUNT
FAILURE
AI ACTION
EXPECTED NET
CONFIDENCE
STATUS
```

Do not make it visually noisy.

Use:
- fine horizontal separators;
- strong typography;
- small metadata labels;
- subtle status treatments.

Important cases may receive a gold left/top rule rather than a large colored badge.

---

# 14. Case Detail Page

The case page should answer five questions immediately:

1. What failed?
2. How much revenue is at risk?
3. What does RecoveryOS recommend?
4. Why?
5. Is the action allowed?

Recommended layout:

```text
Case header
│
├── Payment / customer context
│
├── Financial value
│
├── Candidate action comparison
│
├── Guardrail result
│
├── Approval state
│
├── AI explanation
│
└── Audit timeline
```

---

# 15. Candidate Action Comparison

For each action show:

```text
ACTION
Probability
Expected gross recovery
Intervention cost
Expected net revenue
Allowed / blocked
```

The selected action should be visually emphasized with:
- gold rule;
- subtle accent background;
- clear “SELECTED” label.

Do not hide alternatives. Showing alternatives is important to demonstrate that the optimizer actually considered choices.

---

# 16. Guardrail Presentation

Guardrails are a core differentiator.

Present them clearly.

Example:

```text
POLICY CHECK

✓ Recovery window valid
✓ Retry limit available
✓ Incentive budget available
✓ Expected value above threshold

STATUS
APPROVED FOR EXECUTION
```

For blocked actions:

```text
ACTION BLOCKED

Retry limit reached.

RecoveryOS selected:
DO NOTHING
```

Never use visual design that makes a blocked action look executable.

---

# 17. Approval UI

Approval-required cases must feel deliberate.

Show:

```text
APPROVAL REQUIRED

High-value recovery case

Amount
₹25,000

Recommended action
Retry later

Expected net recovery
₹18,450

Confidence
81%

Reason
Amount exceeds automatic execution threshold.
```

Buttons:

```text
Approve
Reject
```

Approve is the primary gold action.

Reject is an outline/secondary action.

---

# 18. Buttons

## Primary

- gold background;
- white text;
- 6px radius;
- minimum 44px height;
- medium weight;
- slight tracking.

Hover:
- shift toward `#D4A84B`;
- subtle shadow;
- optional `translate-y-0.5`.

## Secondary

- transparent;
- foreground border;
- rich black text.

Hover:
- muted background;
- gold border/text.

## Ghost

- no border;
- muted foreground;
- gold underline on hover.

Transition:

```text
200ms ease-out
```

---

# 19. Inputs

Inputs should be calm and editorial.

```text
height: 44–48px
border: 1px solid var(--border)
background: transparent or white
radius: 6px
```

Focus:

```text
2px gold ring
gold border
```

Placeholder:
- warm gray;
- reduced opacity.

Always provide visible labels.

---

# 20. Charts

Use **Recharts**.

Charts should feel like editorial data visualizations.

Preferred:
- thin lines;
- restrained fills;
- ivory background;
- white chart surface;
- gold as primary data emphasis.

Do not create:
- rainbow charts;
- excessive gradients;
- 3D charts;
- decorative chart clutter.

Recommended visualizations:

### Revenue recovery comparison

Baseline vs RecoveryOS.

### Recovery funnel

```text
Failed
→ Eligible
→ Actioned
→ Recovered
```

### Action distribution

Show:
- retry now;
- retry later;
- reminder;
- incentive;
- escalate;
- do nothing.

### Incremental revenue

Show cumulative incremental recovery over simulation batches.

Always include readable legends and labels.

---

# 21. Simulator Page

The simulator is one of the most important pages for the demo.

Layout:

```text
SIMULATION LAB

Parameters
├── Dataset size
├── Random seed
└── Run simulation

Results
├── Baseline recovery
├── AI recovery
├── Intervention cost
├── Incremental recovery
└── Net incremental recovery

Comparison chart

Case-level examples
```

The strongest result should be the **net incremental recovery**.

---

# 22. Audit Timeline

Use a vertical editorial timeline.

Example:

```text
11:42:18
PAYMENT_FAILED
Payment failed due to insufficient funds.

11:42:19
PREDICTIONS_GENERATED
6 candidate actions evaluated.

11:42:19
OPTIMIZATION_COMPLETED
Retry later selected.

11:42:19
GUARDRAIL_PASSED
Within merchant policy.

11:43:04
ACTION_EXECUTED
Retry requested.

11:43:05
PAYMENT_RECOVERED
₹4,999 recovered.
```

Use IBM Plex Mono for timestamps/event types.

---

# 23. Navigation

Navigation should be minimal.

Suggested:

```text
RecoveryOS

Command Center
Recovery Queue
Simulator
Policies
Audit
```

Optional utility area:
- environment;
- merchant;
- system status.

Avoid large navigation bars with too many items.

---

# 24. Logo / Wordmark

Use:

```text
RecoveryOS
```

in Playfair Display.

The wordmark should be simple.

Optional gold detail:
- a thin rule;
- a small dot;
- subtle accent mark.

Do not create a complicated AI robot logo.

---

# 25. Decorative Elements

Allowed:
- thin rules;
- subtle circles/rings;
- paper/noise texture;
- soft ambient gold glow;
- layered editorial compositions.

Use these sparingly.

The UI must remain usable if decorative effects are removed.

---

# 26. Paper Texture

A very subtle noise/paper texture may be applied globally.

Opacity:

```text
~30% of the texture asset's own subtlety
```

It must never make text harder to read.

Prefer CSS/background asset rather than expensive runtime rendering.

---

# 27. Ambient Glow

Optional:

```text
large blurred gold circle
opacity around 2%
```

Use only in hero/empty/background areas.

Never place glowing effects behind critical financial numbers.

---

# 28. Motion

Motion philosophy:

**Restrained and inevitable.**

Default:

```text
200ms ease-out
```

Subtle entrance:

```text
opacity 0 → 1
duration ~600ms
```

Allowed:
- opacity;
- border transitions;
- shadow transitions;
- subtle button lift;
- underline reveal.

Avoid:
- bounce;
- overshoot;
- spinning loaders used decoratively;
- excessive parallax;
- large transforms;
- flashy AI animations.

Respect:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

# 29. Responsive Design

## Mobile < 768px

- single-column layouts;
- metrics become 2-column where practical;
- tables become scrollable or transform into cards;
- buttons stack where necessary;
- maintain generous spacing;
- preserve typography hierarchy.

All interactive elements:

```text
minimum 44 × 44px
```

No horizontal overflow.

---

# 30. Accessibility

Must include:

- semantic HTML;
- correct heading hierarchy;
- visible keyboard focus;
- labels for form controls;
- meaningful alt text;
- sufficient contrast;
- keyboard-accessible dialogs;
- accessible status messaging;
- reduced-motion support.

Do not rely on color alone for:
- success;
- failure;
- blocked;
- approval;
- selected action.

---

# 31. Component Architecture

Build reusable components.

Suggested:

```text
components/
├── layout/
│   ├── AppShell
│   ├── PageHeader
│   └── Section
├── typography/
│   ├── Eyebrow
│   ├── DisplayNumber
│   └── RuleHeading
├── data-display/
│   ├── MetricCard
│   ├── DataTable
│   ├── StatusBadge
│   └── AuditTimeline
├── recovery/
│   ├── RecoveryQueue
│   ├── RecoveryCaseCard
│   ├── ActionComparison
│   ├── GuardrailPanel
│   └── ApprovalPanel
├── charts/
│   ├── RecoveryComparisonChart
│   ├── ActionDistributionChart
│   └── IncrementalRevenueChart
└── controls/
    ├── Button
    ├── Input
    ├── Select
    └── Dialog
```

Do not create one-off styling for every page.

---

# 32. Design Token Implementation

Tokens must be centralized.

Preferred:

```text
frontend/src/styles/tokens.css
frontend/src/styles/globals.css
```

Tailwind should consume the same token values where practical.

Do not create conflicting values such as:

```text
gold-1
gold-2
brand-yellow
primary-yellow
ai-gold
```

There should be one canonical accent.

---

# 33. Do Not Violate This Design

The coding agent must NOT:

- switch to Inter as the primary font;
- use default system typography everywhere;
- use blue/purple AI gradients;
- use neon colors;
- use glassmorphism;
- make every component pill-shaped;
- make every card heavily shadowed;
- use excessive rounded corners;
- create dense dashboard layouts;
- use giant colorful status badges;
- add decorative animations everywhere;
- replace serif headlines with sans-serif;
- replace ivory with pure white as the main page background;
- add random colors not defined by the design system.

---

# 34. Design Quality Test

Before completing a frontend feature, ask:

1. Does it look editorial?
2. Is Playfair Display used for major hierarchy?
3. Is Source Sans 3 used for operational UI?
4. Are technical labels in IBM Plex Mono?
5. Is the ivory/gold/black palette preserved?
6. Are rule lines used where appropriate?
7. Is there enough whitespace?
8. Is the page too visually noisy?
9. Is the financial hierarchy obvious?
10. Are buttons and states accessible?
11. Does it work on mobile?
12. Does it look like RecoveryOS rather than a generic AI SaaS template?

If several answers are “no”, revise the design before shipping.

---

# 35. Final Visual Direction

RecoveryOS should feel like:

**A premium editorial financial intelligence console.**

Not:

**A generic AI dashboard.**

The design should communicate the same product principle as the architecture:

**Intelligence with restraint. Automation with control. Revenue decisions with evidence.**
