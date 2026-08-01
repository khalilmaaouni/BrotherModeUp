HISTORICAL source archive (2026-08-02). Superseded by docs/craft/FABLE-PRODUCT-CRAFT-RESEARCH-REVIEW.md, which reviews this plan with verdict REVISE and twelve amendments; the review file governs.
The body below is the unmodified original from Downloads, SHA256 a1303e4fc4d27e20c35d9bfe701d48348ac0473e1009a494717868c55118ea32. Strip everything above and including the marker line to re-derive it.
<!-- verbatim original below -->
# BrotherME Product Craft Upgrade

## Research, Architecture Recommendations, User Flows, and Fable-Governed Implementation Loops

**Document status:** Proposed implementation program for Fable review  
**Prepared:** 2026-08-01  
**Target repository:** `khalilmaaouni/BrotherModeUp`  
**Assumption:** The BrotherME Final Release Closure Plan has already been implemented: release truth, one SQLite authority, atomic project service, executable lifecycle, consent-first setup, security boundaries, runtime adapters, evidence, and release validation are stable  
**Mandatory gate:** Fable must inspect the current repository, challenge this program, remove unnecessary scope, and return `GO` before implementation starts  
**Primary outcome:** Make BrotherME reliably produce end-to-end products that are useful, clear, platform-appropriate, beautiful, accessible, performant, localized in context, maintainable, and independently verified

---

# 1. Executive recommendation

BrotherME should add an optional, progressively loaded **Product Craft capability pack** rather than adding design instructions to its permanent core.

The capability pack should convert a founder’s goal into a governed product-craft lifecycle:

```text
Outcome and user understanding
→ evidence-based experience research
→ information architecture and complete state map
→ three materially different design directions
→ founder selection
→ one approved brand and design system
→ one thin end-to-end vertical slice
→ rendered visual and functional review
→ systematic implementation
→ context-aware localization
→ motion and media where justified
→ device, accessibility, performance, and language verification
→ independent Fable review
→ delivery evidence
```

The upgrade must preserve BrotherME’s defining strengths:

- proportionality;
- founder control;
- durable state;
- explicit work identity;
- one writer per file;
- mechanical evidence;
- post-final-edit verification;
- honest limits;
- load-on-demand context;
- human-gated learning;
- provider-independent architecture;
- simple user-facing language.

The central design decision is:

> Product craft is a governed execution domain inside BrotherME, not a second operating system beside BrotherME.

All durable craft decisions and evidence must enter the existing BrotherME project service. Markdown, Figma frames, screenshots, Storybook, visual diffs, translation files, media, and provider outputs are referenced artifacts or generated views. None may become a competing project truth.

---

# 2. Definition of success

BrotherME succeeds when a solo founder can describe a meaningful product outcome and receive:

1. A clear product direction.
2. A user journey that simply works.
3. A distinctive but appropriate visual identity.
4. A coherent design system.
5. Correct web, mobile, and tablet behavior.
6. Purposeful motion rather than decoration.
7. High-quality media when it adds product value.
8. Translation and localization based on the full product context.
9. Complete normal, empty, loading, failure, permission, recovery, and success states.
10. Accessibility and performance evidence.
11. Rendered screenshots or device evidence after the final relevant change.
12. An honest list of what remains unverified.
13. A final result Fable independently reviews against the approved product direction.

“Beautiful” alone is insufficient.

A successful product must be:

```text
Useful
Understandable
Trustworthy
Recoverable
Accessible
Responsive
Platform-appropriate
Fast enough
Culturally and linguistically appropriate
Visually coherent
Distinctive where it matters
Maintainable
Verified
```

---

# 3. Non-negotiable architecture constraints

## 3.1 The BrotherME core remains small

Do not place the following in the always-loaded core:

- design-style catalogs;
- visual-reference examples;
- platform guidelines;
- component-library documentation;
- motion documentation;
- localization rules for every language;
- provider-specific instructions;
- media-generation prompts.

The core only learns:

- when to route to Product Craft;
- which safety and founder gates remain active;
- how to read craft status;
- how to present one next action.

Everything else loads only when its trigger applies.

## 3.2 One authority

Craft records live through the existing BrotherME project service and store.

Do not create:

- a craft SQLite database;
- a JSON craft registry;
- a Figma file as authority;
- a Storybook metadata authority;
- a translation-management authority that can silently override project decisions.

External tools remain sources, editors, renderers, or delivery systems.

## 3.3 Provider output is untrusted

Output from Figma, Mobbin, v0, Magic Patterns, 21st.dev, shadcn registries, Motion, Rive, Higgsfield, fal, Runway, Lokalise, Phrase, or any other provider is:

- input to a decision;
- not automatically approved;
- not automatically installed;
- not automatically published;
- not evidence of production quality until inspected in the real product.

## 3.4 Function before ornament

The sequence is always:

```text
User goal
→ journey
→ information hierarchy
→ states and recovery
→ platform behavior
→ content
→ visual direction
→ motion and media
```

A visually memorable interface that hides the main action, breaks on tablet, excludes users, miscommunicates in Japanese, or performs poorly fails.

## 3.5 Review the render, not only the source

No customer-facing screen is accepted from code inspection alone.

Required:

- render;
- inspect;
- test;
- record evidence;
- fix;
- rerender.

## 3.6 Design decisions remain founder-gated

Fable recommends.

The founder approves:

- final brand direction;
- major visual direction;
- material platform divergence;
- premium external dependencies;
- likeness or identity-based media;
- high-cost media generation;
- high-risk transcreation;
- final delivery.

## 3.7 Failure degrades without corrupting the core

A failed Figma, Mobbin, image, video, or localization provider cannot break BrotherME’s project lifecycle.

It may:

- mark a craft task blocked;
- provide a manual fallback;
- preserve existing state;
- report the limitation.

This follows BrotherME’s “never block the system because one helper failed” principle while still refusing to call the product accepted without required evidence.

---

# 4. Compatibility with BrotherME’s laws

This capability must be reviewed against the current `SKILL.md`, `INVARIANTS.md`, and approved founder rules at implementation time.

## 4.1 Triage: SIMPLE versus COMPLEX

### Simple craft task

Examples:

- fix one misaligned button using an existing component;
- update one approved color token;
- correct one contextual translation;
- add one missing empty state based on an approved pattern;
- replace one asset without changing composition.

Use the shortest path:

```text
Retrieve applicable rules
→ inspect existing system
→ implement one seam
→ render affected state
→ verify
```

Do not trigger a three-direction design process.

### Complex craft task

Examples:

- new product;
- new customer journey;
- new brand;
- major redesign;
- mobile application;
- tablet adaptation;
- multi-locale launch;
- expressive motion system;
- generated campaign media.

Use the complete Product Craft flow.

Applying the full flow to a one-line style correction is `OVERTHOUGHT`. Skipping research, states, platform behavior, and rendered verification for a new product is `UNDERTHOUGHT`.

## 4.2 Founder rules retrieval

Before substantial product-craft work:

- retrieve applicable approved rules using BrotherME’s standard recorded path;
- include product, brand, design, accessibility, localization, and provider rules;
- name applied rule IDs in the close report;
- never let a learned preference weaken accessibility, security, privacy, or evidence gates.

## 4.3 Constitution outranks taste

No learned design preference may override:

- accessibility;
- honest reporting;
- founder approvals;
- data privacy;
- licensing;
- one-writer ownership;
- post-edit verification;
- platform safety;
- release truth.

## 4.4 Beginner response contract

Every user-facing craft response:

- begins with the outcome;
- recommends one next action;
- uses plain language;
- gives ranges with assumptions;
- hides internal component IDs, screenshot hashes, provider payloads, and token names unless advanced detail is requested.

## 4.5 Safety floor

Before writes:

- inspect current Git status;
- establish the active write scope;
- record ownership before dispatch;
- isolate parallel writers;
- verify after the final edit;
- attach visual and functional evidence to the final commit.

## 4.6 Losslessness

Approved craft decisions must survive:

- restart;
- compaction;
- provider outage;
- generated-view deletion;
- Figma unlinking;
- translation-platform disconnect.

## 4.7 Exactly once

A retried provider operation must not:

- duplicate installed components;
- create duplicate reference records;
- publish duplicate assets;
- append duplicate localization context;
- create repeated alerts.

Changed content must still create a new version.

## 4.8 Lifecycle isolation

A new product or later redesign must not silently inherit:

- rejected brand directions;
- old media prompts;
- superseded component decisions;
- old locale approvals;
- screenshots from another lifecycle.

Reusable approved tokens and components require explicit linkage.

## 4.9 Single writer

Only one active task may own a component or screen file in a shared tree.

Parallel visual work uses isolated worktrees or non-overlapping scopes.

## 4.10 Honest reporting

BrotherME may say:

```text
The checkout flow is visually verified on the tested phone, tablet, and desktop viewports.
```

only when those renders exist after the final relevant change.

It may not say:

```text
The experience works everywhere.
```

## 4.11 Failed writes preserve the previous state

Token generation, component installation, translation updates, asset generation, and design-view rendering use atomic writes or rollbackable staging.

## 4.12 Load on demand

Suggested new routing entries:

| Situation | Load |
|---|---|
| New visual product, major customer-facing flow, redesign | `references/craft-director.md` |
| Design research and references | `references/craft-research.md` |
| Brand direction or voice | `references/brand.md` |
| Tokens, components, or design system | `references/design-system.md` |
| Web/mobile/tablet behavior | `references/platform-design.md` |
| Animation or interactive media | `references/motion.md` |
| Image/video generation | `references/creative-media.md` |
| Translation or locale expansion | `references/localization.md` |
| Rendered product review | `references/visual-review.md` |

---

# 5. Research method

This program is based on primary official documentation and current product capabilities reviewed on 2026-08-01.

The research asks five questions for every source:

1. What mechanism creates quality?
2. Which part is reusable inside BrotherME?
3. Which part should remain an optional adapter?
4. Which risks or limitations must BrotherME add?
5. What evidence proves the integration works?

The recommendation deliberately separates:

- visual inspiration;
- user-flow evidence;
- component implementation;
- platform rules;
- motion infrastructure;
- localization infrastructure;
- media generation;
- verification.

No single tool covers all of them.

---

# 6. Benchmark findings

## 6.1 Anthropic frontend-design

### Mechanisms that work

Anthropic’s skill explicitly forces:

- purpose and audience understanding;
- a chosen aesthetic direction;
- deliberate differentiation;
- typography decisions;
- cohesive color;
- intentional composition;
- motion;
- atmospheric detail;
- rejection of repeated generic AI patterns.

### BrotherME recommendation

Use it as an optional creative-generation reference inside a broader governed process.

Add:

- evidence-based references;
- three directions;
- platform rules;
- component-system constraints;
- accessibility;
- performance;
- localization;
- rendered independent review.

### Risk

A bold aesthetic prompt can produce visually distinctive but inappropriate or overengineered interfaces if function, platform, and performance are not resolved first.

Primary source:  
https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md

---

## 6.2 UI/UX Pro Max

### Mechanisms that work

- searchable design knowledge;
- style, palette, typography, UX, and chart guidance;
- stack-specific implementation;
- project design-system generation;
- packaging across many agents.

### BrotherME recommendation

Adopt the pattern of:

```text
small router
→ targeted search
→ structured recommendation
→ reusable design output
```

Do not load a massive catalog into every session.

### Risk

Catalog matching can turn design into “industry + style preset.” BrotherME must use persona, product journey, brand truth, and user evidence before aesthetic selection.

Source:  
https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

---

## 6.3 Figma MCP and Code Connect

### Mechanisms that work

Figma’s MCP can expose:

- components;
- variables;
- layout;
- frames;
- annotations;
- design content;
- write-to-canvas capabilities.

Code Connect links Figma components to real code and can improve agent output by returning actual project component references rather than generalized generated code. It supports React, React Native, HTML-based systems, SwiftUI, and Jetpack Compose.

### BrotherME recommendation

Figma is the preferred optional design-tool adapter when a founder uses it.

Use for:

- importing existing systems;
- visual direction boards;
- editable native design artifacts;
- mapping code and design components;
- founder visual approval;
- preserving designer-editable craft.

### Risk

Figma availability and capabilities vary by plan and seat. A Figma frame does not prove technical correctness, responsive behavior, accessibility, performance, or production maintainability.

Primary sources:

- https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server
- https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect
- https://help.figma.com/hc/en-us/articles/35280968300439-Figma-MCP-collection-What-is-the-Figma-MCP-server

---

## 6.4 Mobbin MCP and Page Flows

### Mechanisms that work

Mobbin provides AI agents with search over hundreds of thousands of shipped product screens. It returns screen images and can be accessed from major AI clients through OAuth. Its strength is showing real product flow patterns rather than asking the model to invent every convention.

Page Flows provides recorded user journeys and interaction sequences.

### BrotherME recommendation

Use reference tools for:

- journey research;
- permissions;
- onboarding;
- payment;
- account recovery;
- empty and failure states;
- navigation patterns;
- mobile conventions.

Extract principles, not pixels.

### Risk

Shipped does not mean appropriate, accessible, or legally reusable. References are not user research, and copying a competitor creates trade-dress and product-fit risks.

Primary sources:

- https://mobbin.com/mcp
- https://docs.mobbin.com/mcp/introduction
- https://pageflows.com/

---

## 6.5 v0 design systems, shadcn registries, and 21st.dev

### Mechanisms that work

V0 improves fidelity when given a custom design-system registry and project tokens.

Shadcn’s registry and MCP server allow agents to:

- browse;
- search;
- inspect;
- install;
- use multiple public or private registries;
- work from source code rather than opaque packages.

Current shadcn registries can distribute components, tokens, feature kits, rules, testing, workflows, and other project files. Official documentation also explicitly warns users to review community registry code.

21st.dev provides a large component and block ecosystem and agent-assisted discovery.

### BrotherME recommendation

Build a project-owned allowlisted registry and a governed `reuse → adapt → create` process.

Every adopted item records:

- source;
- version or commit;
- license;
- dependencies;
- purpose;
- states;
- token compatibility;
- accessibility;
- localization;
- tests.

### Risk

An open-code registry can still introduce:

- insecure code;
- incompatible dependencies;
- visual inconsistency;
- poor accessibility;
- weak responsive behavior;
- maintenance burden.

Primary sources:

- https://v0.dev/docs/design-systems
- https://ui.shadcn.com/docs/mcp
- https://ui.shadcn.com/docs/registry
- https://ui.shadcn.com/docs/directory
- https://21st.dev/

---

## 6.6 Magic Patterns

### Mechanisms that work

Magic Patterns supports design exploration from screenshots, Figma, product context, and code-oriented output. Its Figma import uses richer MCP design context and openly notes that interactive code output may not be pixel-perfect to a static frame.

### BrotherME recommendation

Use as an optional exploration and prototyping adapter, especially for visible alternatives and founder collaboration.

### Risk

Generated prototype code is not accepted production code until it uses the project architecture, design system, states, tests, and evidence.

Primary source:  
https://www.magicpatterns.com/docs/documentation/importing/import-from-figma

---

## 6.7 Motion AI Kit and Motion

### Mechanisms that work

Motion’s AI Kit installs targeted skills and MCP support across multiple coding agents. It includes best practices, example search, spring generation, visual transition editing, and performance-oriented review. Motion for React supports layout animations, gestures, and reduced-motion handling.

### BrotherME recommendation

Use Motion as the preferred web React application motion layer when animation exceeds simple CSS.

Adopt:

- purpose-first MotionSpec;
- tokens;
- reduced-motion behavior;
- performance audit;
- visual editor where useful;
- exact source version.

### Risk

Motion AI Kit features and licenses differ, and some SDK capabilities are early or licensed for internal tooling. Do not make premium or alpha features foundational.

Primary sources:

- https://motion.dev/docs/ai-kit-install
- https://motion.dev/docs/react-installation
- https://motion.dev/docs/react-accessibility

---

## 6.8 GSAP, Rive, Lottie, and 3D tools

### GSAP

Best for deliberate coordinated timelines and scroll-based storytelling.

### Rive

Best for interactive vector art controlled by state machines and data binding across web, React, React Native, Apple, Android, and other runtimes. Rive’s current documentation recommends state machines and supports runtime settlement to reduce unnecessary work.

### Lottie

Useful for authored linear vector animation where broad player support and simple playback matter.

### Spline or other 3D tools

Useful only when a product genuinely needs interactive 3D and performance, accessibility, input, and fallbacks are designed.

### BrotherME recommendation

Use a selection ladder. Do not add all libraries.

Primary sources:

- https://gsap.com/docs/v3/Plugins/ScrollTrigger/
- https://rive.app/docs/editor/state-machine/state-machine
- https://rive.app/docs/runtimes/getting-started

---

## 6.9 Apple HIG and Android adaptive design

### Mechanisms that work

Apple’s current design principles emphasize:

- purpose;
- agency;
- responsibility;
- familiarity;
- flexibility;
- simplicity;
- craft;
- delight.

Apple also requires adaptation, accessibility, familiar behavior, and platform consistency.

Android guidance treats adaptive design as the default and recommends reflow, reveal, and presentation changes across phones, foldables, tablets, and resizable windows. Canonical layouts such as list-detail provide reliable expanded-screen structures.

### BrotherME recommendation

Platform conventions are inputs to creative design, not obstacles.

A product may be visually distinctive while preserving:

- back behavior;
- navigation;
- permissions;
- text scaling;
- system surfaces;
- input methods;
- accessibility;
- window adaptation.

Primary sources:

- https://developer.apple.com/design/human-interface-guidelines/design-principles
- https://developer.apple.com/design/human-interface-guidelines/
- https://developer.apple.com/design/human-interface-guidelines/accessibility/
- https://developer.android.com/design/ui/mobile/guides/layout-and-content/adapt-layout
- https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts

---

## 6.10 Storybook, Chromatic, Playwright, and axe

### Mechanisms that work

- Storybook makes components and states explicit.
- Chromatic or equivalent services create reviewable visual changes.
- Playwright produces deterministic flow and screenshot comparisons.
- axe catches many automated accessibility issues.

Playwright warns that screenshot rendering can vary by operating system and environment. Baselines therefore need pinned, reproducible rendering environments.

### BrotherME recommendation

Require two streams:

```text
Source, semantics, and state audit
+
Rendered experience audit
```

### Risk

Snapshot tests can preserve a bad design. Updating baselines without human review converts regression protection into approval theater.

Primary sources:

- https://storybook.js.org/
- https://www.chromatic.com/docs/visual-tests/
- https://playwright.dev/docs/test-snapshots
- https://github.com/dequelabs/axe-core

---

## 6.11 MessageFormat 2, CLDR, Fluent, and localization platforms

### Mechanisms that work

MessageFormat 2 is a Unicode standard for dynamic localizable messages. It supports:

- variable movement;
- locale-aware number and time formatting;
- plural and selector logic;
- multiple-value matching;
- semantic markup.

CLDR 47 moved MessageFormat 2 to Stable and describes it as infrastructure for natural-sounding interfaces across languages and cultures.

Fluent treats a message as the localization unit and gives translators control over grammar and variants.

Localization platforms add:

- screenshots;
- message context;
- comments;
- glossary;
- translation memory;
- review state;
- QA;
- platform variants.

### BrotherME recommendation

Use a Localization Context Graph and screenshot-linked review. Do not prescribe MF2 when the selected stack’s implementation is immature; preserve the invariants with a mature framework.

### Risk

A standard message syntax does not fix poor source copy, missing product context, weak translation, or bad layouts.

Primary sources:

- https://messageformat.unicode.org/
- https://messageformat.unicode.org/docs/quick-start/
- https://cldr.unicode.org/downloads/cldr-47
- https://projectfluent.org/fluent/guide/hello.html
- https://docs.lokalise.com/en/articles/2045882-screenshots

---

## 6.12 Higgsfield, fal, Runway, and media generation

### Mechanisms that work

These services expose image and video generation, editing, continuation, and creative-model access through APIs, MCP, or agent tooling.

### BrotherME recommendation

Add one provider-neutral Creative Asset interface and treat media as a governed project artifact with:

- brief;
- references;
- continuity;
- consent;
- cost;
- provider;
- model;
- settings;
- output hash;
- license or rights note;
- human approval;
- product-context review.

Higgsfield should be an optional first-class MCP adapter when the user connects it.

### Risk

Generation quality is not legal clearance, consent, brand fit, localization quality, or production readiness.

Primary sources:

- https://higgsfield.ai/mcp
- https://higgsfield.ai/skills
- https://docs.fal.ai/
- https://docs.dev.runwayml.com/

---

# 7. Research conclusion

The best tools do not win because their models have magically better taste.

They win by reducing uncertainty:

| Quality mechanism | Strong examples |
|---|---|
| Clear aesthetic intent | Anthropic frontend-design |
| Structured searchable design knowledge | UI/UX Pro Max |
| Existing design-system context | Figma Code Connect, v0 registries |
| Shipped product references | Mobbin, Page Flows |
| Reusable source components | shadcn, 21st.dev |
| Visual exploration | Magic Patterns, Figma |
| Motion knowledge and editing | Motion AI Kit, Rive, GSAP |
| Explicit platform conventions | Apple HIG, Material and Android adaptive guidance |
| State enumeration | Storybook |
| Rendered comparison | Playwright, Chromatic |
| Context-rich language | MessageFormat, Fluent, localization platforms |
| High-end media generation | Higgsfield, fal, Runway |
| Independent review | BrotherME/Fable governance |

BrotherME should integrate the mechanisms into one accountable lifecycle.


# 8. Recommended BrotherME architecture

## 8.1 Capability-pack model

Create one optional pack:

```text
brotherme-product-craft
```

It contains:

- one craft coordinator skill;
- targeted references;
- deterministic scripts;
- provider adapters;
- render and evidence helpers;
- stack-specific implementation kits.

Do not expose nine unrelated public skills to the founder.

Internally, the coordinator may load:

```text
craft-research
craft-journeys
craft-brand
craft-system
craft-platform
craft-motion
craft-media
craft-localization
craft-review
```

## 8.2 Public interaction

The founder continues to use:

```text
/brotherme <goal>
```

BrotherME decides whether the craft pack applies.

Advanced aliases may exist, but the default user should not need to learn a new command vocabulary.

Example:

```text
/brotherme Build a calming breathing app for anxious people in Japan.
```

BrotherME responds with the recommended next decision, not a menu of design tools.

## 8.3 Internal package structure

```text
brotherme/
  craft/
    core/
      models.py
      policies.py
      scoring.py
      context.py
    services/
      craft_service.py
      reference_service.py
      design_system_service.py
      localization_service.py
      visual_evidence_service.py
      media_service.py
    adapters/
      base.py
      figma.py
      mobbin.py
      registry.py
      storybook.py
      playwright.py
      chromatic.py
      motion.py
      rive.py
      higgsfield.py
      fal.py
      runway.py
      localization_tms.py
    renderers/
      design_brief.py
      design_system.py
      screen_specs.py
      localization_context.py
      review_packet.py
    kits/
      web/
      expo/
      ios/
      android/
      flutter/
```

## 8.4 Service boundary

The craft pack may call approved project-service operations:

```text
create_craft_brief
version_craft_brief
record_reference
propose_direction
select_direction
version_design_system
record_component_adoption
record_screen_spec
record_motion_spec
record_localization_context
record_media_asset
record_visual_evidence
record_craft_review
raise_craft_alert
resolve_craft_alert
```

It may not:

- change core task state outside service operations;
- edit approvals;
- change founder rules;
- change release evidence;
- bypass review;
- write provider credentials;
- directly update unrelated core tables.

## 8.5 Storage

Use the existing authoritative SQLite database.

Add normalized tables only when queried or transactionally important. Store larger structured payloads as validated JSON where that avoids premature schema complexity.

Recommended minimum:

```text
craft_briefs
craft_references
craft_directions
craft_system_versions
craft_components
craft_screen_specs
craft_motion_specs
craft_localization_contexts
craft_media_assets
craft_visual_evidence
craft_reviews
```

Every row includes:

- project ID;
- lifecycle ID where relevant;
- version;
- state;
- actor;
- source;
- created time;
- supersession linkage;
- content hash where appropriate.

## 8.6 Generated artifacts

Generate human-readable views:

```text
DESIGN.md
design/CRAFT-BRIEF.md
design/REFERENCES.md
design/BRAND-DIRECTION.md
design/DESIGN-SYSTEM.md
design/COMPONENTS.md
design/JOURNEYS.md
design/SCREENS.md
design/MOTION.md
localization/GLOSSARY.md
localization/CONTEXT-REPORT.md
evidence/CRAFT-REVIEW.md
```

These are disposable views. Deleting one and regenerating it must produce equivalent content from the store.

## 8.7 Artifact provenance

Every imported or generated artifact records:

- provider or source;
- original URI;
- retrieval date;
- version;
- license or terms note;
- input hash;
- output hash;
- transformation;
- approving human;
- linked task;
- final usage.

## 8.8 Provider adapter law

Each adapter implements a capability contract.

```python
class CraftProvider:
    def capabilities(self) -> dict: ...
    def health(self) -> dict: ...
    def privacy_summary(self) -> dict: ...
    def estimate_cost(self, operation) -> dict: ...
    def execute(self, operation, spec) -> dict: ...
    def normalize_evidence(self, result) -> dict: ...
```

The core does not know provider-specific payloads.

## 8.9 Capability quality labels

Every provider integration is labeled:

- `verified`;
- `verified_with_limits`;
- `documentation_verified`;
- `experimental`;
- `unavailable`.

A provider name in a configuration file is not proof of integration.

---

# 9. Canonical craft records

## 9.1 Craft Brief

```yaml
craft_brief_id:
project_id:
lifecycle_id:
product_type:
platforms:
primary_persona:
secondary_personas:
jobs_to_be_done:
critical_user_journeys:
functional_outcome:
emotional_outcome:
business_outcome:
brand_maturity:
existing_design_sources:
existing_component_sources:
accessibility_target:
performance_target:
supported_locales:
content_maturity:
visual_ambition:
motion_ambition:
media_needs:
constraints:
anti_goals:
unknowns:
evidence_quality:
status:
approved_by:
approved_at:
version:
```

## 9.2 Experience Reference

```yaml
reference_id:
project_id:
reference_type:
source:
source_uri:
product_or_creator:
relevant_persona:
relevant_journey:
relevant_problem:
principles:
evidence:
applicability:
do_not_copy:
legal_or_license_note:
captured_by:
captured_at:
status:
```

## 9.3 Journey Spec

```yaml
journey_id:
project_id:
name:
persona:
goal:
entry:
steps:
decisions:
permissions:
failure_points:
recovery:
completion:
analytics_signals:
platform_variants:
locale_risks:
accessibility_risks:
approved:
```

## 9.4 Brand Direction

```yaml
direction_id:
project_id:
name:
thesis:
audience_truth:
brand_promise:
personality:
anti_personality:
voice:
tone_by_situation:
visual_keywords:
anti_visual_keywords:
typography_direction:
color_direction:
shape_language:
image_direction:
icon_direction:
motion_personality:
references:
distinctiveness:
implementation_cost:
accessibility_risk:
performance_risk:
localization_risk:
status:
approved_by:
approved_at:
```

## 9.5 Design System Version

```yaml
design_system_id:
project_id:
version:
selected_direction_id:
platform_strategy:
token_format:
tokens:
typography:
color:
spacing:
sizing:
radius:
elevation:
borders:
grids:
breakpoints:
density:
themes:
iconography:
illustration:
photography:
motion:
content_rules:
accessibility_rules:
localization_rules:
performance_rules:
component_registry:
platform_overrides:
approved_by:
approved_at:
```

## 9.6 Component Record

```yaml
component_id:
project_id:
name:
purpose:
source_type:
source_uri:
source_version:
license:
dependencies:
adoption_type:
token_mapping:
variants:
states:
keyboard_behavior:
screen_reader_behavior:
touch_behavior:
responsive_behavior:
platform_behavior:
localization_behavior:
performance_note:
security_note:
tests:
visual_evidence:
status:
```

## 9.7 Screen Spec

```yaml
screen_id:
project_id:
journey_id:
name:
purpose:
persona:
entry_conditions:
primary_action:
secondary_actions:
information_hierarchy:
content_requirements:
component_ids:
states:
responsive_behavior:
tablet_behavior:
platform_behavior:
localization_risks:
accessibility_risks:
performance_risks:
motion_spec_ids:
media_asset_ids:
acceptance_checks:
status:
```

## 9.8 Motion Spec

```yaml
motion_spec_id:
project_id:
name:
purpose:
trigger:
affected_elements:
level:
implementation:
duration:
easing_or_spring:
distance:
interruption_behavior:
repeat_behavior:
reduced_motion_behavior:
performance_budget:
evidence:
status:
```

## 9.9 Localization Context

```yaml
message_id:
project_id:
source_locale:
source_text:
source_meaning:
product_area:
journey_id:
screen_id:
component_id:
component_role:
user_action:
user_state:
persona:
brand_voice:
tone:
formality:
preceding_message:
following_message:
variables:
plural_and_selector_rules:
character_limit:
line_limit:
screenshot_ref:
bounding_box:
platform:
device_class:
target_locales:
regional_notes:
glossary_terms:
forbidden_terms:
legal_sensitivity:
transcreation_required:
accessibility_note:
review_status:
```

## 9.10 Media Asset

```yaml
asset_id:
project_id:
purpose:
placement:
format:
dimensions:
duration:
creative_brief:
shot_or_frame_list:
style_references:
subject_references:
brand_constraints:
localization_variants:
provider:
model:
settings:
source_assets:
consent_status:
rights_note:
cost:
output_uri:
content_hash:
status:
approved_by:
```

## 9.11 Visual Evidence

```yaml
visual_evidence_id:
project_id:
task_id:
commit_sha:
screen_or_component:
platform:
device:
viewport:
theme:
locale:
state:
motion_preference:
render_environment:
screenshot_uri:
screenshot_hash:
baseline_uri:
diff_uri:
automated_checks:
reviewer:
findings:
status:
created_at:
```

## 9.12 Craft Review

```yaml
craft_review_id:
project_id:
commit_sha:
review_type:
reviewer:
reviewer_model:
inputs:
criteria:
findings:
severity_counts:
verdict:
required_actions:
created_at:
superseded_by:
```

---

# 10. User-flow architecture

The craft process must serve different starting conditions.

## 10.1 Flow A: New end-to-end product

```text
Goal
→ craft diagnosis
→ product brief
→ reference research
→ journey and information architecture
→ three directions
→ founder selection
→ design system
→ vertical slice
→ rendered review
→ full implementation
→ localization
→ final verification
→ delivery
```

## 10.2 Flow B: Existing product improvement

```text
Goal
→ inspect current product and system
→ identify the highest-value failure
→ preserve what already works
→ propose targeted direction
→ implement one vertical slice
→ compare before and after
→ expand only after evidence
```

Do not perform a full rebrand when the user needs a checkout fix.

## 10.3 Flow C: Design-system adoption

```text
Inventory
→ detect duplication and drift
→ choose token authority
→ map existing components
→ identify gaps
→ migrate one component family
→ visual and functional verification
→ gradual adoption
```

## 10.4 Flow D: Localization upgrade

```text
Source-copy audit
→ message extraction
→ context enrichment
→ glossary
→ framework selection
→ pseudolocalization
→ target translation
→ rendered locale review
→ human approval for high-risk content
→ release
```

## 10.5 Flow E: Brand and marketing site

```text
Audience and promise
→ market and non-software references
→ three brand directions
→ founder selection
→ identity and content system
→ page architecture
→ media and motion plan
→ implementation
→ conversion, performance, accessibility review
→ localized campaign variants
```

## 10.6 Flow F: Motion or media enhancement

```text
Purpose
→ current experience review
→ simplest effective medium
→ brief
→ exploration
→ approval
→ implementation
→ reduced-motion and fallback
→ performance and context review
```

## 10.7 Flow G: Tiny visual correction

```text
Existing system
→ one scoped edit
→ render affected state
→ verify
```

---

# 11. Product-craft diagnosis

Before loading the full pack, BrotherME asks or infers:

1. Is this a new product or existing product?
2. Which platforms matter now?
3. Who is the primary user?
4. What must the user accomplish?
5. Is there an existing brand or design system?
6. Which locales matter?
7. Is visual distinction central to success?
8. Does motion or generated media materially help?
9. What is the accessibility target?
10. What is the time and budget constraint?

The user does not see ten questions at once.

BrotherME resolves from repository and prior decisions first, then asks only decisions that change scope.

---

# 12. Product quality hierarchy

BrotherME evaluates in this order.

## Level 1: Works

- user can complete the primary task;
- state is preserved;
- errors are handled;
- recovery exists;
- data is correct;
- security and permissions are correct.

## Level 2: Understandable

- purpose is clear;
- hierarchy is clear;
- labels are clear;
- consequences are clear;
- status and feedback are clear.

## Level 3: Accessible and adaptable

- assistive technologies work;
- text scales;
- keyboard and touch work;
- reduced motion works;
- layouts adapt;
- locale variation works.

## Level 4: Coherent

- typography;
- spacing;
- color;
- components;
- content;
- motion;
- imagery;
- platform behavior form one system.

## Level 5: Distinctive and delightful

- the experience has a memorable point of view;
- differentiation serves the product;
- craft reinforces trust and emotional value;
- no generic decoration replaces product substance.

A Level 5 product cannot compensate for a Level 1 failure.

---

# 13. Required design states

Every material screen or component specifies applicable states:

- default;
- hover;
- focus;
- pressed;
- selected;
- disabled;
- loading;
- partial loading;
- empty;
- no results;
- validation error;
- system error;
- offline;
- permission required;
- permission denied;
- success;
- destructive confirmation;
- expired;
- unavailable;
- recovery;
- long content;
- translated;
- RTL;
- reduced motion;
- high contrast;
- large text.

The design-system generator must not create only happy-path components.

---

# 14. Reference research protocol

## 14.1 Required sources for complex work

- real product flows;
- official platform guidance;
- current project design and components;
- visual references outside the category;
- accessibility guidance;
- localization considerations;
- competitor patterns;
- anti-references.

## 14.2 Reference analysis

Every reference produces:

```text
Problem solved
User and context
Pattern
Why it works
Evidence quality
What applies
What does not apply
Legal or copying concern
```

## 14.3 Reference mixing

Do not combine incompatible patterns.

Example:

- a luxury editorial visual system;
- dense enterprise dashboard information;
- playful game motion;
- native medical consent flow;

may each work individually but conflict in one product.

Fable explicitly identifies the synthesis principle.

## 14.4 Inspiration versus implementation

Visual source galleries such as Awwwards, Godly, Land-book, Behance, Dribbble, and Figma Community support creative exploration.

They do not prove:

- usability;
- accessibility;
- performance;
- mobile behavior;
- conversion;
- localization;
- production code quality.

---

# 15. Three-direction law

For complex new visual work, Fable must review three materially different directions before founder approval.

## 15.1 Difference criteria

Directions differ across at least five:

- hierarchy;
- composition;
- typography;
- density;
- color behavior;
- image strategy;
- shape language;
- navigation;
- interaction rhythm;
- motion personality.

## 15.2 Direction packet

Each direction includes:

- thesis;
- user fit;
- brand fit;
- primary screen;
- complex screen;
- mobile;
- tablet;
- component sample;
- error or empty state;
- motion sample;
- translated sample;
- accessibility risks;
- performance risks;
- implementation range;
- distinctive memory.

## 15.3 Fable recommendation

Fable recommends one direction based on:

- product usefulness;
- user fit;
- brand truth;
- platform fit;
- differentiation;
- maintainability;
- accessibility;
- localization;
- delivery budget.

Visual excitement alone does not win.

---

# 16. Vertical-slice-first implementation

Do not build the entire design system or all screens before proving the selected direction.

Choose one vertical slice containing:

- entry;
- meaningful user action;
- data or content;
- validation;
- failure;
- success;
- responsive behavior;
- one localized variant;
- one material motion moment where applicable.

Example:

```text
Discover service
→ select option
→ enter details
→ handle validation error
→ confirm
→ see success
```

The slice proves:

- architecture;
- tokens;
- components;
- content;
- platform behavior;
- motion;
- localization;
- visual quality;
- test setup.

Only then expand.

This is the strongest rework-control mechanism in the plan.


# 17. Fable operating model

## 17.1 Fable responsibilities

Fable is:

- research lead;
- product strategist;
- experience architect;
- craft director;
- plan author;
- delegation orchestrator;
- architecture guardian;
- visual reviewer;
- localization reviewer;
- final judge.

Fable does not become the routine implementation writer.

## 17.2 Lower Claude Builder responsibilities

The lower Claude Builder:

- implements approved designs;
- creates tokens;
- builds components;
- writes stories and tests;
- integrates platform behavior;
- implements motion specs;
- extracts messages;
- generates pseudolocales;
- applies findings;
- produces evidence.

## 17.3 Fast Worker responsibilities

The Fast Worker performs deterministic low-risk work:

- token conversion;
- fixture generation;
- screenshot-matrix generation;
- repetitive Storybook states;
- asset optimization;
- localization-context extraction from known metadata;
- glossary checks;
- registry inventory.

## 17.4 Founder responsibilities

The founder decides:

- product promise;
- scope;
- selected direction;
- brand;
- provider budget;
- material creative risk;
- high-risk media;
- transcreation;
- final acceptance.

## 17.5 Review separation

Every meaningful craft task follows:

```text
Fable brief
→ lower model implementation
→ deterministic checks
→ rendered evidence
→ Fable adversarial review
→ lower model fixes
→ rerender
→ Fable final review
```

---

# 18. Mandatory Fable pre-implementation review

Save as:

```text
docs/craft/FABLE-PRODUCT-CRAFT-RESEARCH-REVIEW.md
```

Use this prompt:

```text
You are Fable acting as BrotherME's release architect and product-craft director.

Review the current BrotherME repository and the attached Product Craft Upgrade
research and implementation plan.

Assume the release-closure architecture is implemented, but verify that
assumption from the code and evidence. Do not implement.

Your purpose is to ensure the Product Craft upgrade:
- respects every BrotherME law;
- uses the existing project service and store;
- preserves proportionality;
- does not create a second source of truth;
- does not weaken security, evidence, accessibility, or release gates;
- creates better end-to-end products rather than prettier screenshots;
- remains practical for one founder.

Return exactly:

A. VERDICT
GO | REVISE | STOP

B. CURRENT ARCHITECTURE CHECK
For every assumption this plan makes:
- verified;
- partly verified;
- false;
- evidence.

C. LAW COMPATIBILITY
Review triage, founder rules, founder gates, beginner contract, safety floor,
losslessness, exactly-once behavior, lifecycle isolation, single writer, honest
reporting, failed-write safety, and load-on-demand context.

D. REMOVE OR DEFER
Identify anything that increases surface, token cost, dependency risk, or
maintenance without materially improving user outcomes.

E. MISSING CAPABILITIES
Identify missing product, UX, brand, accessibility, platform, motion, media,
localization, testing, or provider concerns.

F. ARCHITECTURE DECISION RECORD
Approve or reject:
- optional capability pack;
- one public BrotherME command;
- existing SQLite authority;
- provider adapters;
- generated views;
- three-direction law;
- vertical-slice-first implementation;
- render-review loop;
- Localization Context Graph;
- Fable planning and review with lower-model execution.

G. REORDERED LOOPS
Give the minimum dependency order and identify what may safely run in parallel.

H. FIRST SIX IMPLEMENTATION BRIEFS
Each brief must name:
- user value;
- failure closed;
- readable files;
- writable files;
- forbidden files;
- acceptance checks;
- rendered evidence;
- rollback;
- time and token range.

I. QUALITY GATES
Convert beauty, usability, delight, platform fidelity, localization, and polish
into observable evidence.

J. FINAL AMENDMENTS
Provide exact changes to this document.

Do not approve breadth for its own sake.
Prefer one coherent lifecycle over many disconnected integrations.
Return GO only when implementation can begin without weakening BrotherME.
```

Implementation starts only after:

- Fable `GO`;
- founder approves scope;
- no Critical architecture concern;
- target branch and work scopes exist;
- baseline tests and evidence are recorded.

---

# 19. Loop 0 — Architecture confirmation and capability freeze

## Goal

Confirm the release-closure foundation and approve the smallest Product Craft scope.

## Dependency

None.

## Fable work

- run the mandatory review;
- inspect current BrotherME laws and store;
- verify project-service extension points;
- inspect command routing and dynamic references;
- verify runtime render capabilities;
- decide first supported product stacks;
- create the accepted/deferred provider matrix.

## Builder work

Only documentation and generated inventory after Fable approval:

- record architecture decision;
- create capability feature flags;
- create empty package skeleton;
- add no functional provider code.

## Deliverables

```text
docs/craft/FABLE-PRODUCT-CRAFT-RESEARCH-REVIEW.md
docs/craft/PRODUCT-CRAFT-ADR.md
docs/craft/PROVIDER-MATRIX.md
docs/craft/QUALITY-GATES.md
```

## Exit gates

- Fable GO;
- no second state system;
- exact supported stack scope;
- exact adapter scope;
- feature freeze;
- baseline release tests green.

## Rollback

Delete the empty pack and docs. No migration.

## Efficiency guidance

Do not let the first loop become implementation.

## Range

- Time: 0.5–1.5 working days.
- Effective tokens: 50k–120k.
- Confidence: Medium.

---

# 20. Loop 1 — Craft data model and project-service integration

## Goal

Create durable craft records without weakening BrotherME’s store.

## Dependencies

Loop 0.

## Fable work

- approve record boundaries;
- decide normalized versus JSON fields;
- define versioning;
- define idempotency;
- define lifecycle isolation;
- define permission and approval rules;
- write migration brief.

## Builder work

Implement:

- craft tables;
- data validation;
- project-service operations;
- content hashing;
- supersession;
- attribution;
- generated-view hooks;
- migration;
- backup and recovery;
- export.

## Critical properties

- one transaction per state-changing operation;
- retries do not duplicate;
- old lifecycle artifacts do not leak;
- deleted generated views can be rebuilt;
- provider identifiers cannot become project IDs;
- no provider credential is stored;
- a failed write leaves the prior version intact;
- craft work can be disabled.

## Required tests

- migration from current schema;
- interrupted migration;
- duplicate reference;
- duplicate asset;
- superseded direction;
- rejected direction;
- project lifecycle reuse;
- generated-view deletion;
- concurrent writes;
- malformed payload;
- unsupported provider;
- export and reimport where supported;
- permission failure.

## Fable adversarial review

Attempt:

- split-brain between `DESIGN.md` and SQLite;
- duplicate media creation;
- accepted screen referencing rejected direction;
- locale approval from previous lifecycle;
- provider result that bypasses founder approval;
- craft record that changes task state without service.

## Exit gates

- migrations pass;
- all operations attributed;
- invariant tests calibrated;
- no parallel authority;
- full core gate remains green;
- Fable accepts the transaction design.

## Rollback

Restore pre-migration backup. The pack must remain off until migration succeeds.

## Parallelization

None for schema writers. Read-only review may run in parallel.

## Range

- Time: 2–4 working days.
- Tokens: 180k–450k.
- Confidence: Low before schema inspection.

---

# 21. Loop 2 — Router, proportionality, and progressive loading

## Goal

Make Product Craft appear automatically when valuable and disappear when unnecessary.

## Dependencies

Loop 1.

## Fable work

- define trigger taxonomy;
- define simple and complex examples;
- define required references by route;
- review user-facing language;
- define one-next-action behavior.

## Builder work

Implement:

- craft diagnosis;
- simple-path routing;
- complex-path routing;
- stack and locale detection;
- existing-system detection;
- dynamic reference loader;
- capability availability report;
- user-visible craft status.

## Routing examples

### Do not load full craft pack

- backend-only API;
- one existing-token change;
- typo;
- simple approved component reuse;
- one translation correction.

### Load targeted module only

- translation: localization;
- animation: motion;
- responsive bug: platform;
- brand copy: brand and localization;
- component adoption: design system.

### Load complete flow

- new product;
- redesign;
- new mobile/tablet application;
- new brand;
- multi-market launch.

## Token-economy tests

Measure prompt/context size for:

- trivial UI fix;
- one component;
- one screen;
- full product;
- localization-only task.

The trivial path must not load large reference catalogs.

## Exit gates

- simple task remains simple;
- complex task cannot bypass craft planning;
- only applicable references load;
- no new public command required;
- beginner responses preserve BrotherME contract;
- context cost documented.

## Rollback

Disable craft router and retain manual invocation.

## Parallelization

Reference-file authoring can run in separate non-overlapping lanes after route design approval.

## Range

- Time: 1–2.5 days.
- Tokens: 80k–220k.
- Confidence: Medium.

---

# 22. Loop 3 — Research and reference engine

## Goal

Ground design in real product, platform, and brand evidence without copying.

## Dependencies

Loops 1–2.

## Fable work

- define research query templates;
- define source quality;
- define reference analysis;
- define legal and copying warnings;
- select initial adapters.

## Builder work

Implement:

- manual reference capture;
- URL and screenshot references;
- Figma context import;
- Mobbin optional MCP;
- project component and Storybook inventory;
- official platform-guideline references;
- reference normalization;
- reference report renderer;
- anti-reference handling.

## Recommended first adapters

1. Manual/URL reference.
2. Project repository and Storybook.
3. Figma MCP.
4. Mobbin MCP.
5. shadcn registry metadata.

Defer broad gallery scraping.

## Research output

For each design problem:

```text
Observed pattern
Source
User context
Why it works
Evidence strength
Applicability
Risk
What not to copy
```

## Required tests

- unavailable provider;
- unauthenticated provider;
- duplicate result;
- source removed;
- reference belongs to wrong platform;
- reference contains untrusted instructions;
- screenshot without license context;
- project already has an equivalent pattern.

## Security

Reference content is untrusted data. It cannot instruct BrotherME to:

- change architecture;
- install dependencies;
- expose credentials;
- weaken gates;
- copy proprietary content.

## Exit gates

- research runs without any paid provider;
- provider failure has fallback;
- references have analysis;
- no reference automatically creates code;
- Fable can trace each selected principle;
- founder can understand the recommendation.

## Rollback

Disable providers; retain normalized reference records.

## Parallelization

Independent read-only research sources may run in one wave.

## Range

- Time: 1.5–3 working days.
- Tokens: 120k–320k.
- Confidence: Medium.

---

# 23. Loop 4 — Journey, information architecture, and state completeness

## Goal

Ensure the product simply works before visual design expands.

## Dependencies

Craft Brief and research.

## Fable work

- identify primary persona;
- define jobs-to-be-done;
- map critical journeys;
- decide navigation;
- define information hierarchy;
- define error and recovery;
- define platform differences;
- define analytics or success signals.

## Builder work

Implement:

- journey-record service;
- screen inventory;
- state matrix;
- flow diagrams;
- generated journey view;
- journey validation;
- test templates.

## Required journey review

For each primary journey:

- entry;
- user intent;
- minimum steps;
- decisions;
- data;
- permissions;
- progress;
- validation;
- failure;
- recovery;
- completion;
- next action.

## Required product states

No critical journey may omit:

- loading;
- empty or initial state;
- validation;
- service failure;
- permission failure where applicable;
- recovery;
- success.

## Exit gates

- primary journey can be explained in one minute;
- no dead end;
- no state depends on undefined copy;
- phone/tablet/web differences identified;
- high-risk decisions founder-approved;
- Fable marks journey ready for visual direction.

## Rollback

Journey versions are superseded, not overwritten.

## Parallelization

Independent secondary journeys can be researched in parallel after the primary architecture is approved.

## Range

- Time: 1.5–3 days.
- Tokens: 120k–300k.
- Confidence: Medium.

---

# 24. Loop 5 — Three directions and founder selection

## Goal

Create intentional visual differentiation without premature implementation.

## Dependencies

Loops 3–4.

## Fable work

- write direction briefs;
- assign visual exploration;
- judge product fit;
- compare risks;
- recommend one direction;
- present one founder decision.

## Lower-model work

Create three direction packets using:

- existing design context;
- approved references;
- platform guidance;
- required states;
- representative content;
- one localized example.

Possible tools:

- Figma;
- Magic Patterns;
- local HTML prototypes;
- v0;
- image generation for mood and composition only.

## Direction evidence

Each direction includes rendered:

- primary surface;
- complex surface;
- phone;
- tablet;
- error or empty state;
- one long-locale sample;
- one motion concept if relevant.

## Direction score

Fable assesses:

- user clarity;
- product fit;
- brand truth;
- differentiation;
- platform fidelity;
- accessibility;
- localization;
- performance;
- maintainability;
- implementation risk.

## Anti-pattern gate

Reject:

- three palette variants;
- generic gradient plus bento layout;
- directions invented without references;
- inaccessible typography;
- motion-heavy concept without reduced-motion path;
- direction requiring unapproved paid dependency;
- direction impossible on target platforms.

## Exit gates

- three materially different options;
- Fable recommendation;
- founder approval;
- rejected directions preserved as rejected;
- implementation cannot begin against an unapproved direction.

## Rollback

Founder may select another proposed direction before system implementation. After system implementation, a direction change triggers reforecast and new lifecycle version.

## Parallelization

Three design explorations may run in parallel with separate scopes. Fable synthesizes.

## Range

- Time: 1.5–4 days.
- Tokens: 180k–500k.
- Confidence: Medium.

---

# 25. Loop 6 — Brand, tokens, and design-system foundation

## Goal

Turn the selected direction into a reusable system.

## Dependencies

Selected direction.

## Fable work

- approve brand thesis;
- define positive and anti-traits;
- approve typography;
- approve color roles;
- decide platform variance;
- decide initial component scope;
- review licensing.

## Builder work

Implement:

- DTCG-compatible tokens;
- platform token outputs;
- theme and preference modes;
- typography;
- grids;
- density;
- icon and image rules;
- motion tokens;
- content rules;
- `DESIGN.md`;
- validation and drift tests.

## Token layers

- primitive;
- semantic;
- component;
- platform;
- motion;
- content and localization;
- preference modes.

## Typography checks

- license;
- embedding;
- script coverage;
- target platforms;
- weight availability;
- numerals;
- body legibility;
- fallback;
- load performance;
- Japanese/Arabic/Cyrillic coverage where needed.

## Color checks

- semantic roles;
- light and dark;
- high contrast;
- color-blind differentiation;
- data visualization;
- platform materials;
- cultural risk;
- contrast.

## Exit gates

- one token authority;
- generated platform outputs agree;
- existing components can consume tokens;
- no hardcoded parallel theme in new work;
- typography covers target locales;
- accessibility and performance tests;
- Fable approves system foundation.

## Rollback

Revert generated platform outputs and restore prior system version.

## Parallelization

After token contract freezes:

- web output;
- native output;
- documentation;
- tests;

may run in parallel.

## Range

- Time: 2–5 days.
- Tokens: 200k–520k.
- Confidence: Low to Medium.

---

# 26. Loop 7 — Component registry and implementation kits

## Goal

Give the builder reusable, vetted components without creating a collage.

## Dependencies

Loop 6.

## Fable work

- approve component precedence;
- define first component families;
- define adoption rubric;
- approve external registries;
- review high-impact components.

## Builder work

Implement:

- project component inventory;
- component records;
- Storybook stories;
- shadcn registry configuration for web where appropriate;
- registry search and preview;
- license/dependency checks;
- token mapping;
- accessibility tests;
- platform kit instructions.

## Initial component families

Only what the vertical slice needs:

- buttons and links;
- inputs;
- selection;
- navigation;
- feedback and alerts;
- dialogs and sheets;
- list/card/item;
- loading/empty/error;
- layout primitives;
- data display if required.

## Component precedence

1. Existing approved project component.
2. Platform-native component.
3. Approved project registry.
4. Approved external registry.
5. Custom.

## Acceptance

Every component has:

- purpose;
- variants;
- states;
- accessibility behavior;
- platform behavior;
- localization behavior;
- tests;
- visual evidence;
- source and license.

## Registry security

Before install:

- inspect source;
- pin version or commit;
- inspect dependencies;
- run security checks;
- apply in isolated branch;
- verify affected files;
- refuse unreviewed install scripts.

## Exit gates

- vertical-slice component set complete;
- no duplicate styling system;
- components use tokens;
- required states exist;
- registry provenance recorded;
- Fable design-system review passes.

## Rollback

Component adoption occurs in isolated commits and can be reverted without deleting project state.

## Parallelization

Different component families may run in parallel when files and dependencies do not overlap.

## Range

- Time: 2–5 days.
- Tokens: 180k–480k.
- Confidence: Medium.

---

# 27. Loop 8 — Thin end-to-end vertical slice

## Goal

Prove product direction, system, platform behavior, content, and verification before full build.

## Dependencies

Loops 4–7.

## Fable work

- select slice;
- define scope;
- define states;
- define viewports;
- define locales;
- define evidence;
- write implementation brief.

## Builder work

Implement one complete journey slice.

Required:

- entry;
- real content;
- action;
- validation;
- failure;
- recovery;
- success;
- responsive behavior;
- tablet behavior where targeted;
- one locale expansion;
- reduced motion;
- accessibility;
- tests;
- screenshots.

## Evidence

- Storybook component states;
- Playwright flow;
- screenshot matrix;
- accessibility;
- performance;
- locale render;
- commit;
- visual review.

## Fable review

Fable attacks:

- generic AI appearance;
- hierarchy;
- usability;
- incomplete states;
- platform mismatch;
- content;
- component drift;
- localization;
- visual polish;
- performance.

## Decision

After review:

- continue;
- revise system;
- change direction;
- stop.

This is the last cheap point for major direction changes.

## Exit gates

- primary slice works;
- no Critical/High review findings;
- founder confirms direction in real product;
- system modifications are incorporated;
- forecast updated;
- full build approved.

## Rollback

Discard slice branch or retain as prototype evidence. Do not pollute the final system with rejected code.

## Parallelization

Implementation is serial inside the slice’s shared files. Read-only reviewers may run in parallel.

## Range

- Time: 2–5 days.
- Tokens: 220k–550k.
- Confidence: Low.

---

# 28. Loop 9 — Motion system and interactive media

## Goal

Add motion only where it improves feedback, continuity, understanding, or brand.

## Dependencies

Approved vertical slice.

## Fable work

- classify motion needs;
- choose implementation level;
- approve MotionSpecs;
- review accessibility and performance;
- approve expressive moments.

## Motion ladder

1. None.
2. CSS/native transition.
3. Motion or native declarative animation.
4. GSAP timeline.
5. Rive interactive state machine.
6. Produced/generated video.

Stop at the first sufficient level.

## Builder work

- implement motion tokens;
- integrate selected library;
- implement reduced-motion alternatives;
- create motion stories/tests;
- capture video evidence;
- measure performance;
- verify interruption and repeated input.

## Motion acceptance

- named purpose;
- no blocked task;
- no unexpected layout shift;
- keyboard and screen-reader behavior intact;
- reduced-motion design;
- mobile thermal and performance consideration;
- no repeated distracting loop;
- no motion-only meaning.

## Exit gates

- MotionSpec and implementation agree;
- reduced motion passes;
- Fable accepts render;
- performance budget passes;
- library licensing recorded.

## Rollback

Every expressive motion has a static or simpler fallback.

## Parallelization

Independent motion components can run in parallel after tokens and behavior freeze.

## Range

- Time: 1–4 days.
- Tokens: 100k–320k.
- Confidence: Medium.

---

# 29. Loop 10 — Creative media and Higgsfield adapter

## Goal

Allow excellent image and video creation without weakening governance.

## Dependencies

Brand and screen specs.

## Fable work

- define media need;
- decide create, source, photograph, illustrate, or generate;
- approve brief;
- choose provider;
- approve exploration;
- approve final use.

## Builder work

Implement provider-neutral media service:

```text
capabilities
estimate
generate
edit
extend
localize
history
download
normalize evidence
```

Initial adapters:

- manual asset;
- Higgsfield MCP;
- optional fal;
- optional Runway.

## Media record

- purpose;
- placement;
- dimensions;
- duration;
- references;
- subject;
- consent;
- rights;
- provider/model;
- settings;
- cost;
- source hash;
- output hash;
- approval;
- localization variants.

## Media user flow

```text
Brief
→ low-cost exploration
→ Fable selection
→ founder approval when material
→ final generation
→ optimization
→ context render
→ accessibility and performance
→ approval
```

## Security and privacy

- provider auth stays outside project files;
- clearly disclose what is uploaded;
- avoid sensitive client data;
- do not generate real-person likeness without consent;
- no automatic publication;
- no unreviewed text embedded in imagery;
- preserve originals.

## Exit gates

- manual fallback;
- provider failure safe;
- cost shown;
- rights/consent recorded;
- final media reviewed in product;
- responsive crops and captions;
- no Critical content issue.

## Rollback

Remove the generated asset and restore previous approved asset without modifying core state history.

## Parallelization

Independent asset explorations may run in parallel under a shared brief.

## Range

- Time: 1.5–3 days engineering, generation time variable.
- Tokens: 100k–260k plus provider cost.
- Confidence: Medium.

---

# 30. Loop 11 — Context-aware localization and transcreation

## Goal

Make every locale correct in meaning, product context, brand, and layout.

## Dependencies

Stable journeys, screens, source copy, and design system.

## Fable work

- review source copy;
- define localization strategy;
- define locale risk;
- approve glossary;
- choose framework;
- classify functional copy versus transcreation;
- review high-risk locales and messages.

## Builder work

Implement:

- semantic message IDs;
- extraction;
- Localization Context Graph;
- screenshots and bounding boxes;
- glossary;
- framework integration;
- MessageFormat 2 or mature equivalent;
- pseudolocales;
- RTL;
- locale test matrix;
- TMS adapter where selected;
- evidence.

## Source-copy gate

Refuse translation when source is:

- ambiguous;
- concatenated;
- overloaded across meanings;
- dependent on English wordplay without transcreation;
- missing variable meaning;
- missing consequence;
- legally unsafe.

## Translation modes

### Functional

Controls, forms, settings, errors.

### Product adaptation

Onboarding, education, notifications, empty states.

### Transcreation

Hero, tagline, campaign, emotional copy, video.

## Required adversarial cases

- `Continue` used in multiple meanings;
- Japanese formality;
- Arabic RTL and mixed numerals;
- German expansion;
- Russian/Arabic/Czech plural categories where relevant;
- names and addresses;
- dates, time, currencies, units;
- gender and pronouns;
- variable reordering;
- legal or consent text;
- truncation;
- voiceover or video timing.

## Visual localization

For each launch locale:

- render key journeys;
- inspect layout;
- inspect type coverage;
- inspect line breaks;
- inspect icons and direction;
- inspect cultural imagery/color;
- inspect interaction;
- capture evidence.

## Human review

Require human or qualified locale review for:

- legal;
- medical;
- financial;
- safety;
- public brand campaigns;
- transcreated taglines;
- voice and likeness;
- locales outside demonstrated model competence.

## Exit gates

- no isolated production strings where context exists;
- no concatenation;
- dynamic messages correct;
- glossary respected;
- screenshots linked;
- RTL and long text pass;
- high-risk approval recorded;
- Fable localization review passes.

## Rollback

Locale bundles are versioned. Revert target locale without altering source records.

## Parallelization

Independent locales may run in parallel after source and glossary freeze. Shared message architecture remains one writer.

## Range

- Time: 3–8 days depending on locales.
- Tokens: 250k–800k.
- Confidence: Low.

---

# 31. Loop 12 — Full product expansion and continuous rendered review

## Goal

Expand from the proven vertical slice without losing quality.

## Dependencies

Loops 8–11 as applicable.

## Fable work

- group screens into coherent waves;
- define briefs;
- enforce system;
- review every wave;
- reforecast;
- prevent scope expansion.

## Builder work

Implement product by waves:

1. primary journeys;
2. supporting journeys;
3. settings and administration;
4. rare and recovery states;
5. marketing and documentation surfaces;
6. final locale and device coverage.

## Wave law

Each wave:

```text
brief
→ implementation
→ deterministic tests
→ rendered matrix
→ Fable review
→ fixes
→ rerender
→ merge
```

Do not defer all visual review to the end.

## Drift detection

Detect:

- hardcoded colors or spacing;
- duplicate components;
- unregistered fonts;
- missing states;
- missing localization context;
- screenshot gaps;
- motion without spec;
- asset without provenance;
- platform behavior divergence.

## Exit gates

- every primary journey accepted;
- every relevant state rendered;
- design-system drift zero or approved;
- no unresolved Critical/High;
- evidence linked to latest commits;
- status remains understandable.

## Rollback

Wave-level commits and feature flags.

## Parallelization

Disjoint journeys and platforms may use worktrees. Shared design-system files remain serial.

## Range

Project-dependent; estimate after the vertical slice.

---

# 32. Loop 13 — Final craft convergence, dogfood, and release

## Goal

Prove that a solo founder can use the complete system and ship a product that works.

## Dependencies

All applicable loops.

## Validation products

Use at least:

- one new product;
- one existing-product improvement;
- one multilingual product;
- one mobile or tablet experience.

BrotherME’s own UI must not be the only test.

## External users

Minimum:

- one non-technical founder;
- one experienced frontend or product engineer;
- one user working in a non-English locale;
- one different operating system.

## Measurements

- time to direction;
- number of founder decisions;
- implementation rework;
- visual review cycles;
- accessibility findings;
- localization findings;
- performance;
- tokens;
- paid provider cost;
- completion;
- user understanding;
- product task success;
- comparison with plain coding-agent workflow.

## Final Fable review

Fable reviews:

- architecture;
- laws;
- user experience;
- source;
- renders;
- localization;
- motion;
- performance;
- accessibility;
- provider evidence;
- release claims.

## Release gates

- no Critical/High;
- real end-to-end product delivered;
- external-user evidence;
- exact commit evidence;
- supported providers and stacks labeled;
- known limits explicit;
- founder GO.

## Range

- Engineering: 2–5 days.
- Observation: at least 7 calendar days.
- Tokens: 200k–550k.
- Confidence: Medium.


# 33. Provider recommendation matrix

The goal is not to integrate every provider. The goal is to preserve a stable contract and select the smallest useful set.

| Capability | Recommended status | Reason |
|---|---|---|
| Project repository and existing components | Native | Highest-trust source of current implementation |
| Manual references and screenshots | Native | Required no-provider fallback |
| Figma MCP | First-class optional adapter | Structured design context and editable design workflow |
| Figma Code Connect | Optional advanced adapter | Connects design components to real code |
| Mobbin MCP | First-class optional research adapter | Real shipped product-flow reference |
| Page Flows | Research reference | Useful flow evidence, no core dependency |
| Anthropic frontend-design | Creative reference/optional subskill | Strong aesthetic direction, insufficient alone |
| UI/UX Pro Max | Searchable reference adapter | Broad design knowledge, must be grounded |
| v0 | Optional exploration adapter | Strong registry and prototype workflow |
| Magic Patterns | Optional exploration adapter | Good visible iteration and design import |
| shadcn MCP/registry | First-class web registry adapter | Open source, inspectable, private registry support |
| 21st.dev | Optional component-discovery source | Broad component exploration |
| Radix/Base UI/React Aria | Recommended web foundations | Accessible interaction primitives |
| Storybook | First-class local evidence | Explicit component states |
| Playwright | First-class web flow and visual evidence | Deterministic browser tests and screenshots |
| Chromatic/Percy | Optional hosted visual review | Useful collaboration, not required |
| Motion | Preferred React motion layer | Strong capability and reduced-motion support |
| Motion AI Kit | Optional agent reference | Best practices and editing tools |
| GSAP | Conditional | Complex storytelling only |
| Rive | Conditional first-class media adapter | Interactive cross-platform animation |
| Lottie | Compatibility option | Linear authored animation |
| Spline/3D | Deferred/conditional | High cost and accessibility/performance risk |
| Higgsfield MCP | First-class optional media adapter | Agent-native image/video workflow |
| fal | Optional alternative media adapter | Broad API model access |
| Runway | Optional alternative media adapter | Versioned media-generation API |
| MessageFormat 2 | Preferred where mature | Standard dynamic-message model |
| Fluent/ICU/i18next/native catalogs | Supported mature alternatives | Stack maturity may be more important |
| Lokalise/Phrase/Crowdin/Tolgee | One selected optional TMS adapter | Do not maintain all initially |
| Apple HIG and Android guidance | Native references | Platform authority |
| Awwwards/Godly/Land-book/Behance | Inspiration only | Not usability evidence |

---

# 34. Recommended first release scope

## 34.1 Include

- Craft Brief.
- Journey and state mapping.
- Reference capture.
- Figma optional import.
- Mobbin optional research.
- Three design directions.
- Founder selection.
- Design-system tokens.
- Component inventory and records.
- shadcn registry adapter for relevant web projects.
- Storybook and Playwright integration.
- Web and Expo implementation kits.
- Apple and Android review rules.
- Tablet adaptive review.
- MotionSpec and Motion integration.
- Localization Context Graph.
- Pseudolocalization and screenshot-linked locale review.
- Higgsfield optional adapter.
- Fable planning and final review.

## 34.2 Defer

- building a visual editor;
- every TMS;
- every image/video provider;
- every frontend framework;
- custom vector-animation editor;
- custom 3D tool;
- cloud team collaboration;
- portfolio design dashboard;
- automatic marketplace crawling;
- autonomous creative publication;
- AI-generated design score without human review.

## 34.3 Initial platform support

### Full workflow

- modern web;
- React/Next.js where present;
- Expo/React Native.

### Review and implementation guidance

- SwiftUI;
- Jetpack Compose;
- Flutter.

Expand full automation only after real usage.

---

# 35. Product stack decision policy

BrotherME must not impose a stack based on trend.

## 35.1 Preserve existing stack when

- it meets requirements;
- maintainers know it;
- component and test infrastructure exist;
- performance is acceptable;
- platform needs are supported.

## 35.2 Change or add stack when

- target platform cannot be delivered reliably;
- accessibility is materially blocked;
- responsive/adaptive requirements cannot be met;
- current system has no maintainable path;
- founder approves migration cost.

## 35.3 Web selection

Prefer:

- semantic platform features;
- established framework in project;
- accessible headless primitives;
- project-owned tokens;
- source-owned components;
- deterministic tests.

## 35.4 Native selection

Prefer native SwiftUI or Compose when:

- deep platform integration;
- advanced system controls;
- platform-specific experience;
- performance;
- accessibility;
- long-term native ownership;

justify separate implementations.

Prefer Expo/React Native when:

- shared team and language;
- cross-platform delivery speed;
- product behavior is mostly shared;
- native escape hatches exist.

## 35.5 Tablet

Treat as an explicit target, not a breakpoint afterthought.

Require:

- window resizing;
- portrait and landscape;
- split-screen;
- keyboard and pointer where applicable;
- expanded navigation;
- multiple panes where useful;
- preserved context.

---

# 36. Design-system policy

## 36.1 Token authority

Use one token source in DTCG-compatible format where practical.

Outputs may generate:

- CSS variables;
- Tailwind configuration;
- React Native tokens;
- Swift assets or generated values;
- Compose theme values;
- Figma variables;
- Storybook themes.

## 36.2 Token governance

A token change records:

- reason;
- affected components;
- visual evidence;
- accessibility impact;
- locale impact;
- migration;
- approval.

## 36.3 Component API quality

Components use semantic properties.

Prefer:

```text
tone="danger"
emphasis="primary"
size="compact"
state="loading"
```

over visual implementation properties such as:

```text
red
shadowLarge
rounded20
```

## 36.4 Escape hatches

Allow one-off visual composition where brand differentiation requires it, but:

- keep primitives reusable;
- record the exception;
- avoid copying one-off tokens into global system;
- test and maintain it.

---

# 37. Localization architecture recommendation

## 37.1 Context-first message pipeline

```text
Source UI
→ semantic message ID
→ source-copy review
→ context extraction
→ screenshot linkage
→ glossary and variable metadata
→ translation
→ linguistic review
→ rendered review
→ approval
```

## 37.2 Context extraction

Automatically extract where available:

- route;
- component;
- props;
- neighboring message IDs;
- screenshot state;
- variables;
- character constraints;
- platform.

Require human/Fable completion for:

- meaning;
- tone;
- consequence;
- persona;
- legal sensitivity;
- transcreation.

## 37.3 No duplicate English string assumption

Identical English source strings may require different message IDs and translations.

## 37.4 Locale maturity labels

- machine draft;
- reviewed by fluent model;
- reviewed by native/fluent human;
- domain-approved;
- in-context approved.

The user sees which level applies.

## 37.5 Localized media

Text, subtitles, voice, lip-sync, or culturally adapted imagery require independent locale review even when a provider offers automated localization.

---

# 38. Motion and delight policy

## 38.1 The delight budget

Each primary journey may have a small number of deliberate signature moments.

Examples:

- one meaningful onboarding transition;
- one success moment;
- one branded empty state;
- one coherent navigation transition.

Do not scatter effects across every interaction.

## 38.2 Motion purpose taxonomy

- feedback;
- continuity;
- hierarchy;
- orientation;
- progress;
- causality;
- brand emotion;
- education.

Every MotionSpec selects at least one.

## 38.3 Refusal cases

Refuse or simplify motion when:

- it blocks input;
- causes layout instability;
- conflicts with reduced motion;
- consumes unacceptable bandwidth or battery;
- makes status misleading;
- creates motion sickness risk;
- is present only because the library makes it easy.

---

# 39. Visual review rubric

## 39.1 Function

- primary task succeeds;
- controls are discoverable;
- state is visible;
- error recovery works;
- content is real.

## 39.2 Hierarchy

- first attention is correct;
- primary and secondary actions differ;
- grouping is clear;
- density fits task;
- long pages have structure.

## 39.3 Typography

- hierarchy;
- legibility;
- rhythm;
- language coverage;
- line length;
- line height;
- numeric clarity;
- fallbacks.

## 39.4 Composition

- alignment;
- spacing;
- balance;
- use of negative space;
- adaptation;
- consistency without monotony.

## 39.5 Brand

- thesis visible;
- anti-traits avoided;
- imagery and motion coherent;
- not generic;
- appropriate to trust and audience.

## 39.6 Platform

- native conventions;
- safe areas;
- back behavior;
- system controls;
- input methods;
- responsive/adaptive layout.

## 39.7 Accessibility

- semantic structure;
- focus;
- keyboard;
- screen reader;
- contrast;
- text scale;
- targets;
- motion;
- cognition.

## 39.8 Localization

- meaning;
- grammar;
- terminology;
- layout;
- RTL;
- cultural appropriateness;
- dynamic formatting.

## 39.9 Performance

- loading;
- interaction;
- stability;
- asset cost;
- animation cost;
- low-end behavior.

## 39.10 Maintainability

- tokens;
- components;
- variants;
- tests;
- no duplicated system;
- clear ownership.

---

# 40. Objective quality gates

A product cannot be guaranteed beautiful for every person. BrotherME can guarantee that the defined process and evidence gates run.

## 40.1 Product usefulness gate

- primary task completed in testing;
- no unresolved dead end;
- failure and recovery tested;
- founder/user acceptance.

## 40.2 Design direction gate

- approved thesis;
- three alternatives for complex work;
- selected direction;
- anti-traits;
- representative renders.

## 40.3 Component gate

- required states;
- accessibility behavior;
- platform behavior;
- localization;
- tests;
- visual evidence;
- provenance.

## 40.4 Responsive and tablet gate

- required viewport matrix;
- no overlap or clipping;
- hierarchy remains;
- tablet composition is purposeful;
- input modes work.

## 40.5 Accessibility gate

- automated checks;
- keyboard;
- screen-reader review;
- text scaling;
- reduced motion;
- manual findings resolved.

## 40.6 Localization gate

- contextual message records;
- dynamic-message tests;
- glossary;
- screenshot review;
- RTL/expansion;
- high-risk approval.

## 40.7 Motion gate

- MotionSpec;
- purpose;
- reduced-motion alternative;
- performance;
- render review.

## 40.8 Media gate

- provenance;
- consent;
- rights note;
- cost;
- alt/caption;
- responsive optimization;
- human approval.

## 40.9 Visual evidence gate

- after final change;
- exact commit;
- pinned render environment;
- all required states;
- reviewer findings;
- approval.

## 40.10 Release gate

- no Critical or High craft findings;
- functional and visual streams pass;
- founder accepts;
- Fable GO.

---

# 41. Efficiency controls

## 41.1 Load only what applies

The biggest token-saving decision is progressive loading.

## 41.2 Research once, reference many times

Save approved research and direction as durable artifacts.

## 41.3 Vertical slice before system expansion

Avoid building dozens of components that do not survive real product use.

## 41.4 Existing components first

Do not rewrite working primitives.

## 41.5 One render matrix

Generate viewports, themes, states, and locales from a single manifest.

## 41.6 Stable screenshot environment

Pin browser, fonts, operating system/container, viewport, timezone, locale, animation settings, and network fixtures.

## 41.7 Delta review

After the baseline:

- inspect affected components and journeys;
- run full suite at milestone and release;
- avoid rerendering unrelated products for every tiny change.

## 41.8 Fable reviews decisions and evidence

Do not spend Fable tokens on repetitive implementation.

## 41.9 Lower model gets complete briefs

A clear brief prevents loops, re-reading, and aesthetic improvisation.

## 41.10 Provider selection ladder

Use:

```text
local/project
→ open source
→ connected provider
→ paid generation
```

only as needed.

---

# 42. Token and time planning

These are planning ranges, not promises.

| Workstream | Fable | Lower models | Likely time |
|---|---:|---:|---:|
| Architecture and research review | 50k–120k | 10k–30k | 0.5–1.5 days |
| Store and service integration | 50k–100k | 180k–450k | 2–4 days |
| Routing and references | 30k–70k | 120k–300k | 2–4 days |
| Journeys and directions | 60k–140k | 150k–400k | 2–6 days |
| Design system and components | 60k–140k | 300k–700k | 4–9 days |
| Vertical slice | 50k–120k | 220k–550k | 2–5 days |
| Motion and media | 40k–100k | 160k–450k | 2–6 days |
| Localization | 60k–150k | 250k–800k | 3–8 days |
| Visual QA and release | 70k–160k | 200k–500k | 3–7 days |

Reforecast after:

- Fable architecture review;
- selected direction;
- vertical slice;
- locale scope;
- provider availability.

---

# 43. Suggested repository files

## Core integration

```text
brotherme/craft/__init__.py
brotherme/craft/models.py
brotherme/craft/policies.py
brotherme/craft/services.py
brotherme/craft/context.py
brotherme/craft/scoring.py
```

## Adapters

```text
brotherme/craft/adapters/base.py
brotherme/craft/adapters/figma.py
brotherme/craft/adapters/mobbin.py
brotherme/craft/adapters/registry.py
brotherme/craft/adapters/storybook.py
brotherme/craft/adapters/playwright.py
brotherme/craft/adapters/motion.py
brotherme/craft/adapters/rive.py
brotherme/craft/adapters/higgsfield.py
brotherme/craft/adapters/localization.py
```

## References

```text
references/craft-director.md
references/craft-research.md
references/brand.md
references/design-system.md
references/platform-design.md
references/motion.md
references/creative-media.md
references/localization.md
references/visual-review.md
```

## Scripts

```text
tools/bm_craft.py
tools/bm_craft_render.py
tools/bm_craft_context.py
tools/bm_craft_localize.py
tools/bm_craft_evidence.py
```

## Tests

```text
tools/test_bm_craft_store.py
tools/test_bm_craft_router.py
tools/test_bm_craft_research.py
tools/test_bm_craft_system.py
tools/test_bm_craft_render.py
tools/test_bm_craft_localization.py
tools/test_bm_craft_adapters.py
tools/test_bm_craft_e2e.py
```

## Documentation and evidence

```text
docs/craft/PRODUCT-CRAFT-ADR.md
docs/craft/PROVIDER-MATRIX.md
docs/craft/QUALITY-GATES.md
docs/craft/FABLE-PRODUCT-CRAFT-RESEARCH-REVIEW.md
docs/craft/FABLE-FINAL-CRAFT-REVIEW.md
docs/evidence/craft/
```

Fable must adjust this map to current repository conventions rather than introduce a competing organization.

---

# 44. Exact implementation-brief template

```text
Task:
User value:
Failure being closed:
Why now:
Dependencies:

BrotherME laws that apply:
Founder rules retrieved:

Approved craft brief:
Selected direction:
Journey:
Screen/component:
Platform:
Locales:
Reference principles:
Anti-reference:

Readable files:
Writable files:
Forbidden files:
Active fence/worktree:

Required behavior:
Required states:
Required viewports:
Required themes:
Required locales:
Required motion preference:

Existing component to reuse:
Allowed registry:
Allowed provider:
License/security constraints:

Accessibility checks:
Performance checks:
Localization checks:
Functional checks:
Visual evidence:

Done-check commands:
Expected outputs:
Seeded failure or calibration:
Fable review inputs:

Time range:
Token range:
Confidence:
Rollback:
```

---

# 45. Craft progress view

Default founder-facing view:

```text
Product direction
User journey
Design progress
Current build
What was verified
Language coverage
Risk
Decision needed
Next step
```

Advanced view may show:

- direction IDs;
- component sources;
- provider calls;
- screenshot hashes;
- tokens;
- review scores;
- render matrix;
- locale approval level.

---

# 46. Alerts

## Attention

- reference provider unavailable;
- design estimate moved;
- locale requires human review;
- visual baseline changed;
- component lacks a required state.

## High

- unapproved direction implemented;
- screen has no failure or recovery state;
- component bypasses tokens;
- registry dependency unreviewed;
- layout fails target device;
- translation lacks context;
- accessibility failure;
- animation lacks reduced-motion path;
- provider output used without provenance.

## Critical

- design provider attempts credentials or unsafe write;
- generated media uses unconsented likeness;
- legal/high-risk localization auto-approved;
- visual work weakens security or privacy;
- release claims unrendered support;
- external asset license prohibits intended use;
- project has competing design-system authorities.

Alerts deduplicate by cause.

---

# 47. Final Fable adversarial review prompt

Save result as:

```text
docs/craft/FABLE-FINAL-CRAFT-REVIEW.md
```

Prompt:

```text
Act as BrotherME's hostile final product-craft reviewer.

The founder intends to ship an end-to-end product built with the Product Craft
capability. Attempt to disqualify it.

Review the exact final commit and the authoritative BrotherME records.
Do not trust generated summaries.

Inspect:
- BrotherME law compliance;
- Craft Brief;
- reference analysis;
- journey and state map;
- three directions and founder selection;
- brand direction;
- design-system version;
- component records and provenance;
- real implementation;
- phone, tablet, desktop, and native evidence;
- loading, empty, failure, permission, recovery, and success states;
- Storybook;
- browser/device tests;
- visual comparisons;
- accessibility;
- performance;
- MotionSpecs and reduced-motion renders;
- media provenance, consent, rights, and cost;
- Localization Context Graph;
- glossary;
- translated screenshots;
- MessageFormat/dynamic-message tests;
- Fable and human approvals;
- evidence after the last relevant change.

Return exactly:

A. VERDICT
GO | NO-GO

B. PRODUCT FUNCTION
Critical journeys, failure, recovery, and state integrity.

C. USER EXPERIENCE
Hierarchy, clarity, cognitive load, navigation, feedback, and agency.

D. GENERIC-AI AUDIT
Identify template-like, copied, ornamental, or context-free design.

E. BRAND AND VISUAL SYSTEM
Typography, color, composition, imagery, iconography, consistency, distinction.

F. PLATFORM REVIEW
Web, mobile, tablet, native conventions, input, resizing, and system behavior.

G. ACCESSIBILITY
Automated and manual findings.

H. MOTION
Purpose, interruption, reduced motion, performance, and comfort.

I. MEDIA
Quality, provenance, consent, rights, performance, and cultural fit.

J. LOCALIZATION
Meaning, tone, terminology, dynamic grammar, RTL, expansion, formatting,
cultural appropriateness, screenshots, and reviewer quality.

K. MAINTAINABILITY
Tokens, components, dependencies, tests, and drift.

L. EVIDENCE INTEGRITY
Exact commit, render environment, final-change timing, and missing proof.

M. REQUIRED FIXES
Critical, High, Medium.

N. CLAIMS TO NARROW

O. STRONGEST REASON NOT TO SHIP

Return GO only when no Critical or High finding remains and the primary journeys
have functional and rendered evidence after the final relevant change.
```

---

# 48. Go/no-go matrix

| Gate | GO | NO-GO |
|---|---|---|
| BrotherME laws | All preserved | Craft flow bypasses or weakens one |
| Authority | Existing project service | Second craft truth |
| Product journey | Primary task and recovery pass | Happy path only |
| Direction | Founder approved | Unapproved or generic |
| System | Tokens/components coherent | Duplicate or ad hoc system |
| Mobile | Real phone evidence | Desktop scaled down |
| Tablet | Purposeful adaptive layout | Stretched phone |
| Accessibility | Automated and manual pass | Critical/High finding |
| Motion | Purpose and reduced-motion evidence | Decorative or unsafe |
| Media | Provenance, consent, rights, approval | Missing any |
| Localization | Full context and visual review | Isolated strings or no locale render |
| Performance | Budgets pass | Regressions unresolved |
| Evidence | Latest commit and pinned render | Stale or unverifiable |
| Fable | Final GO | NO-GO |
| Founder | Accepts | Rejects |

---

# 49. Target scorecard

The process can target these scores. Real product quality still requires actual users.

| Metric | Target after implementation |
|---|---:|
| Architecture compatibility | 9.5 |
| Proportionality and efficiency | 9.2 |
| Product usefulness | 9.2 |
| Design research | 9.3 |
| Brand coherence | 9.2 |
| Visual distinction | 9.1 |
| Component quality | 9.3 |
| Responsive web | 9.4 |
| Mobile platform quality | 9.2 |
| Tablet adaptation | 9.2 |
| Accessibility | 9.2 |
| Motion | 9.1 |
| Media governance | 9.1 |
| Localization architecture | 9.5 |
| Translation quality | 8.5–9.3 depending on human review and locale |
| Visual verification | 9.5 |
| Maintainability | 9.2 |
| Solo-founder usability | 9.2 |
| Real-world product success | Cannot honestly exceed 9 without sustained user evidence |

---

# 50. What BrotherME can guarantee

BrotherME can guarantee, within its supported environment, that:

- the applicable craft process was selected;
- required decisions and approvals were recorded;
- a complex product received research and alternatives;
- an approved design system exists;
- required states were specified;
- functional checks ran;
- screenshots were rendered;
- accessibility and performance gates ran;
- localization context exists;
- final evidence follows the last relevant change;
- Fable reviewed the result.

BrotherME cannot guarantee:

- universal aesthetic preference;
- market success;
- perfect human translation without qualified review;
- legal clearance of generated media without appropriate expert review;
- every device behavior without testing;
- perfect accessibility from automated tools;
- a provider’s continued availability.

Honest guarantees are stronger than impossible promises.

---

# 51. Recommended implementation order

The minimum-rework order is:

1. Fable architecture review.
2. Craft records and service boundary.
3. Router and progressive loading.
4. Reference research.
5. Journey and complete states.
6. Three directions.
7. Design-system foundation.
8. Component registry.
9. Thin vertical slice.
10. Motion and media.
11. Localization.
12. Product expansion by reviewed waves.
13. Dogfood and final review.

Do not start with provider adapters, animation libraries, or a design catalog.

---

# 52. Final recommendation

BrotherME’s opportunity is not to become another frontend prompt pack.

It should become the first founder-oriented product-craft operating discipline that connects:

```text
User outcome
Product architecture
Experience research
Brand
Design system
Components
Platform behavior
Motion
Media
Localization
Functional testing
Rendered testing
Independent review
Delivery evidence
```

The competitive advantage is the integration with BrotherME’s existing laws.

Other tools provide excellent pieces:

- Anthropic provides bold aesthetic direction.
- Mobbin provides shipped-product evidence.
- Figma provides structured visual context.
- v0 and shadcn provide design-system-aware source components.
- Motion and Rive provide advanced interaction.
- Higgsfield and media APIs provide creative generation.
- Unicode and localization platforms provide language infrastructure.
- Storybook and Playwright provide rendered verification.

BrotherME should orchestrate these pieces under:

- proportionality;
- founder choice;
- durable state;
- one authority;
- explicit attribution;
- security boundaries;
- post-change evidence;
- Fable judgment.

The founder should experience one simple flow:

```text
Describe the product
→ choose the recommended direction
→ review meaningful milestones
→ receive a verified product
```

The complexity belongs inside BrotherME, loaded only when it creates value.

---

# 53. Primary source index

## BrotherME current architecture

- Repository: https://github.com/khalilmaaouni/BrotherModeUp
- `SKILL.md`
- `INVARIANTS.md`

## AI frontend and design skills

- Anthropic frontend-design:  
  https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md
- Anthropic plugin catalog:  
  https://github.com/anthropics/claude-code/blob/main/plugins/README.md
- UI/UX Pro Max:  
  https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

## Design references and tools

- Figma MCP:  
  https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server
- Figma Code Connect:  
  https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect
- Mobbin MCP:  
  https://mobbin.com/mcp
- Mobbin MCP documentation:  
  https://docs.mobbin.com/mcp/introduction
- Page Flows:  
  https://pageflows.com/
- Magic Patterns Figma import:  
  https://www.magicpatterns.com/docs/documentation/importing/import-from-figma

## Components and design systems

- v0 design systems:  
  https://v0.dev/docs/design-systems
- shadcn MCP:  
  https://ui.shadcn.com/docs/mcp
- shadcn registry:  
  https://ui.shadcn.com/docs/registry
- shadcn directory:  
  https://ui.shadcn.com/docs/directory
- 21st.dev:  
  https://21st.dev/
- Radix:  
  https://www.radix-ui.com/primitives
- Base UI:  
  https://base-ui.com/
- Design Tokens Community Group:  
  https://www.designtokens.org/TR/2025.10/format/

## Platform design

- Apple design principles:  
  https://developer.apple.com/design/human-interface-guidelines/design-principles
- Apple HIG:  
  https://developer.apple.com/design/human-interface-guidelines/
- Apple accessibility:  
  https://developer.apple.com/design/human-interface-guidelines/accessibility/
- Android adaptive layout:  
  https://developer.android.com/design/ui/mobile/guides/layout-and-content/adapt-layout
- Android canonical layouts:  
  https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts
- Expo UI:  
  https://docs.expo.dev/versions/latest/sdk/ui/
- Tamagui:  
  https://tamagui.dev/
- NativeWind:  
  https://www.nativewind.dev/

## Motion and media

- Motion AI Kit:  
  https://motion.dev/docs/ai-kit-install
- Motion React:  
  https://motion.dev/docs/react-installation
- Motion accessibility:  
  https://motion.dev/docs/react-accessibility
- GSAP ScrollTrigger:  
  https://gsap.com/docs/v3/Plugins/ScrollTrigger/
- Rive state machines:  
  https://rive.app/docs/editor/state-machine/state-machine
- Rive runtimes:  
  https://rive.app/docs/runtimes/getting-started
- Higgsfield MCP:  
  https://higgsfield.ai/mcp
- fal:  
  https://docs.fal.ai/
- Runway API:  
  https://docs.dev.runwayml.com/

## Verification

- Storybook:  
  https://storybook.js.org/
- Chromatic:  
  https://www.chromatic.com/docs/visual-tests/
- Playwright screenshots:  
  https://playwright.dev/docs/test-snapshots
- axe:  
  https://github.com/dequelabs/axe-core
- WCAG 2.2:  
  https://www.w3.org/TR/WCAG22/
- Core Web Vitals:  
  https://web.dev/articles/vitals
- Nielsen Norman heuristics:  
  https://www.nngroup.com/articles/ten-usability-heuristics/

## Localization

- MessageFormat 2:  
  https://messageformat.unicode.org/
- MessageFormat 2 Quick Start:  
  https://messageformat.unicode.org/docs/quick-start/
- CLDR 47 release:  
  https://cldr.unicode.org/downloads/cldr-47
- Fluent:  
  https://projectfluent.org/
- Lokalise screenshots:  
  https://docs.lokalise.com/en/articles/2045882-screenshots

## Visual inspiration

Use as inspiration, not product evidence:

- Awwwards: https://www.awwwards.com/
- Godly: https://godly.website/
- Land-book: https://land-book.com/
- Figma Community: https://www.figma.com/community
- Behance: https://www.behance.net/
- Fonts In Use: https://fontsinuse.com/
- Typewolf: https://www.typewolf.com/

---

# 54. Immediate next action

Run the mandatory Fable pre-implementation review against the exact current BrotherME commit.

Do not begin by installing design plugins.

The first deliverable is Fable’s approved architecture and reordered first six implementation briefs.
