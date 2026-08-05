# LENS D: what the Claude Code surface can actually do today

Research for the BrotherMode visual surface design. Scope: measure the harness, do not assume it.

Date of research: 2026-08-05.
Researcher note: every product claim below carries a source. Claims are labelled VERIFIED (read on a page I fetched, or observed first hand on this machine), INFERRED (composed from two or more verified facts, with the composition shown), or UNVERIFIED (could not confirm).

---

## 0. Method, and what surface I measured from

Sources fetched and read in full or in part:

- https://code.claude.com/docs/en/artifacts (the Claude Code artifacts page)
- https://code.claude.com/docs/en/tools-reference (built in tool table)
- https://code.claude.com/docs/en/hooks (hook events and output schema)
- https://code.claude.com/docs/en/plugins (plugin components and layout)
- https://code.claude.com/docs/en/plugins-reference (monitors, `${CLAUDE_PLUGIN_ROOT}`)
- https://code.claude.com/docs/en/skills (skill frontmatter and lifecycle)
- https://code.claude.com/docs/en/statusline (status line contract)
- https://code.claude.com/docs/en/output-styles (output styles)
- https://code.claude.com/docs/en/fullscreen (terminal rendering, mouse)
- https://code.claude.com/docs/en/mcp (MCP surface, resources, elicitation)
- https://code.claude.com/docs/en/channels (pushed events)
- https://code.claude.com/docs/en/settings (settings keys)
- https://code.claude.com/docs/en/llms.txt (the documentation index, used to enumerate every visual page rather than guess)
- https://support.claude.com/en/articles/13979539-custom-visuals-in-chat-and-cowork (inline widgets)
- https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them (claude.ai artifacts)
- https://claude.com/blog/artifacts-in-claude-code (the launch post)

First hand measurements on this machine:

- `claude --version` returns `2.1.207 (Claude Code)`. VERIFIED, run in this session.
- Bundled skills are unpacked at `/private/tmp/claude-1598639508/bundled-skills/2.1.219/`, so the bundled skill payload in play is 2.1.219. VERIFIED, listed in this session.
- The bundled `artifact-capabilities` skill, loaded in this session, states the runtime capability roster available to this user. VERIFIED, read in this session.
- The bundled `artifact-design` skill, loaded in this session, states the theming and CSP rules an artifact author must follow. VERIFIED, read in this session.
- `/private/tmp/claude-1598639508/bundled-skills/2.1.219/fa32f7cf7ecb7e8b7afe3492c0621ede/artifact-capabilities/0.1.17/downloads.d.ts` is the authoritative type contract for the downloads capability. VERIFIED, read in this session.

**Caveat you must carry into the design.** The session I ran this research in is not a plain terminal Claude Code CLI. It exposes an `Artifact` tool with a longer description than the public docs give, and it exposes an MCP server named `visualize` with a `show_widget` tool. Neither of those two extras is documented as part of the Claude Code CLI. Where a finding depends on my session rather than on the CLI contract, I say so explicitly. BrotherMode ships to whatever Claude Code the founder is running, so anything marked "this session only" is not safe to build on.

---

## 1. Headline answer

There is exactly one rich visual surface a BrotherMode plugin can reliably put in front of a user today: **the Artifact**, a self contained HTML or Markdown page published to a private URL on claude.ai, opened in the user's browser, and updatable in place at the same URL.

Everything else the harness offers is either text in the terminal, a native dialog Claude Code draws itself (permission prompts, multiple choice questions), a one line status bar, or a notification. There is no plugin addressable panel inside the terminal, and there is no documented inline widget in Claude Code.

The single most consequential correction to the brief's stated constraints: **inline widgets are not a Claude Code capability.** See section 3.

The second most consequential: **a Claude Code artifact has no persistent storage.** See section 2.6.

---

## 2. The Artifact surface, measured

### 2.1 What it is, and that it exists as a first class tool

VERIFIED. `Artifact` is a built in Claude Code tool. From https://code.claude.com/docs/en/tools-reference, the tool table row reads:

> `Artifact` | Publishes an HTML or Markdown file as an artifact: a private, interactive page on claude.ai. You can share it with a public link, or inside your organization on Team and Enterprise plans, where public sharing requires an Owner to enable it. Requires a Pro, Max, Team, or Enterprise plan and `/login` authentication

The same table's `Permission required` column reads **Yes** for `Artifact`. That matters for the consent constraint, see 2.9.

VERIFIED. From https://code.claude.com/docs/en/artifacts:

> An artifact is a live, interactive web page that Claude Code publishes from your session to a private URL on claude.ai. You open it in a browser, and it updates in place as the session continues.

VERIFIED. The launch post at https://claude.com/blog/artifacts-in-claude-code dates the capability from 18 June 2026 and describes exactly the shape BrotherMode wants:

> Claude Code can capture work progress as an artifact, which turn Claude Code's work into live, shareable visual pages

and names the use cases as "PR walkthroughs, system explainers, dashboards, and release checklists".

### 2.2 Self containment and the Content Security Policy

VERIFIED, quoted from the Page constraints table at https://code.claude.com/docs/en/artifacts:

> **No external requests.** The CSP blocks scripts, stylesheets, fonts, and images loaded from any other host, along with `fetch`, XHR, and WebSocket calls. Claude inlines CSS and JavaScript and embeds images as data URIs so the page renders without any external request. Connector calls are the exception: the page hands them to claude.ai, which makes the network call itself.

> **No backend.** An artifact is a static page. It can't store data submitted through a form or authenticate viewers itself. Its only way to fetch data when someone views it is calling MCP connectors, not an API of its own.

> **Single page.** Relative links do not resolve, because nothing is deployed alongside the page. For multi-section content, Claude uses in-page anchors rather than separate files.

> **Source file types.** The published file must be `.html`, `.htm`, or `.md`. Markdown files render as styled HTML.

> **Rendered size.** The rendered page must be 16 MiB or smaller. Large embedded images are the usual cause when a publish fails for size.

VERIFIED, corroborating from the bundled `artifact-design` skill loaded in this session: "The Artifact CSP blocks font CDNs, so don't link a webfont URL and risk a silent fallback. Instead inline the face as a @font-face data URI."

Practical reading for BrotherMode: inline JavaScript runs. Interactivity inside the page (tabs, filters, sliders, drag and drop, collapsible sections, an in page search) is fully available. Only the network is closed.

### 2.3 Mermaid support

**Split verdict. Read this one carefully.**

NOT FOUND IN PUBLIC DOCUMENTATION. I fetched https://code.claude.com/docs/en/artifacts in full and it does not mention mermaid anywhere. I grepped the entire unpacked bundled skills payload at `/private/tmp/claude-1598639508/bundled-skills/2.1.219/` for the string "mermaid" and got zero hits. A web search restricted to code.claude.com, docs.claude.com, support.claude.com, anthropic.com and claude.com surfaced no page documenting mermaid rendering inside artifacts; the only mermaid results were about a third party Mermaid Chart connector, which is a different thing entirely.

VERIFIED FROM THE TOOL CONTRACT IN THIS SESSION ONLY. The `Artifact` tool description exposed to me in this session states:

> Artifacts render mermaid diagrams natively, markdown via ```mermaid fences, HTML via `<pre class="mermaid">` blocks, no external libraries involved.

That is the tool's own contract, which is a primary source, but it is the contract as exposed to *this* session, and I could not corroborate it in any published page.

**Design instruction.** Treat mermaid as PROBABLE but UNCONFIRMED for the founder's CLI. Do not make a process flow diagram depend on it without a runtime check. The safe path is to author flows and process diagrams as **inline SVG or HTML and CSS**, which is unambiguously supported (the CSP allows anything inline, and the `artifact-design` skill explicitly advises "For generative or decorative graphics, reach for Canvas or WebGL rather than hand-authoring long SVG path data", confirming that both are live). If you want mermaid, the design should degrade to SVG when the fence does not render.

### 2.4 Theming

VERIFIED from the bundled `artifact-design` skill loaded in this session, quoted:

> The page renders in the viewer's theme: `prefers-color-scheme` carries the OS preference, and the viewer's toggle stamps `data-theme="dark"` / `data-theme="light"` on the root element, which must override the media query in both directions.

The skill prescribes a token level pattern: define the palette as custom properties on `:root`, redefine only the tokens under `@media (prefers-color-scheme: dark)`, then redefine them again under `:root[data-theme="dark"]` and `:root[data-theme="light"]`.

This is a first hand product source (Anthropic's own bundled authoring skill), not a published doc page. Label: VERIFIED from the in product authoring contract. Not found on code.claude.com.

VERIFIED from https://code.claude.com/docs/en/artifacts: a design skill is applied automatically, and it reads your project's design system first.

> Claude applies a built-in design skill when it builds an artifact, so pages get a deliberate palette, typography, and layout without extra prompting. Requires Claude Code v2.1.182 or later. That skill also looks for an existing design system in your project before choosing its own.

> Claude treats your design system as higher precedence than its own choices, and your prompt as higher precedence than both.

Design consequence for BrotherMode: putting a colour, type and spacing block in the project `CLAUDE.md` makes every generated artifact adopt the BrotherMode identity without per page prompting. The doc gives the exact shape (a `## Design system` heading listing colors, typography, spacing). That is a cheap, verified lever for a consistent product look.

### 2.5 Updating an existing artifact

VERIFIED from https://code.claude.com/docs/en/artifacts:

> Ask Claude to revise the page, or let a long-running task republish as it makes progress. Claude edits the underlying file and publishes again to the same URL.

> Anyone with the page open sees the update in place. Each publish becomes a version, and from the **Share** control in the page header you can choose which version viewers see.

> To update an artifact from a different session, give Claude the artifact's URL and ask it to revise. Without the URL, a new session always creates a new artifact rather than updating an existing one.

VERIFIED from the blog post: "When Claude Code updates an artifact, the open page refreshes in place and teammates see the updates the moment they're published."

VERIFIED from the same doc: republishing does not re prompt.

> Before publishing a new artifact, Claude Code asks for permission... Republishing an artifact you have already approved does not prompt again.

**This is the single most important mechanic for the founder's complaint.** A live project view that refreshes in place, in front of the founder, across a long run, is directly supported. The cost is one permission prompt at first publish and none afterwards.

**The cross session trap.** "Without the URL, a new session always creates a new artifact rather than updating an existing one." BrotherMode must therefore persist the artifact URL in its SQLite store and hand it back to Claude at the start of every session, or the founder accumulates a graveyard of one shot pages. This is a hard design requirement, not a nicety.

### 2.6 Can it hold state? No.

VERIFIED, and this contradicts a common assumption, so here is the full evidence chain.

1. The Claude Code doc denies it outright: "An artifact is a static page. It can't store data submitted through a form or authenticate viewers itself." (https://code.claude.com/docs/en/artifacts, Page constraints table.)

2. The runtime capability roster available to this user, from the bundled `artifact-capabilities` skill loaded in this session, is exactly two entries:

   > **Available capabilities:** `downloads`, `mcp` (quoted with the source's dash replaced by a comma, wording unchanged), the complete set of capability names you may declare. Anything not listed is unavailable to this user.

   There is no storage, persistence, or state capability on that list.

3. The claude.ai help centre describes something different for *claude.ai chat* artifacts: https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them says "Persistent Storage: Available on Pro, Max, Team, and Enterprise plans" enabling "stateful applications like journals, trackers, and collaborative tools", with a "20 MB storage limit per artifact" and "Text-only input, no images, files, or binary data".

**Resolution: the two surfaces diverge.** Persistent artifact storage is documented for claude.ai chat artifacts, and is absent from both the Claude Code artifacts documentation and the Claude Code runtime capability roster measured on this machine. Design instruction: **do not put any BrotherMode state in the artifact.** This happens to line up perfectly with the constraint that the SQLite store is the single source of truth and every view is generated. The artifact is a render target, never a store.

### 2.7 Can it fetch data? Only through claude.ai MCP connectors, and not on this version.

VERIFIED from https://code.claude.com/docs/en/artifacts:

> An artifact can call MCP connectors each time someone views it, so the page shows current data rather than a snapshot from the session that built it. Connector calls from artifacts are available on Pro, Max, Team, and Enterprise plans and require Claude Code v2.1.209 or later. On earlier versions, Claude publishes the page with whatever data the session gathered while building it.

This machine is on **2.1.207**, which is below that floor. VERIFIED by running `claude --version` in this session.

VERIFIED, and decisive for BrotherMode: local MCP servers cannot be reached from a published page.

> Local MCP servers you configure in Claude Code, such as servers from `.mcp.json`, can supply data while Claude builds the page, but the published page can't call them.

VERIFIED, further constraints on connector backed pages: each viewer's own account makes the call, viewers must approve access first, and

> An artifact that calls connectors can't be shared to a public link on any plan.

**Design instruction.** The artifact cannot read BrotherMode's SQLite store at view time. Not now, not after upgrading past 2.1.209, because the store is local and only claude.ai connectors qualify. Freshness therefore comes from **republishing**, not from fetching. Every render is a snapshot generated from rows at publish time. That is fully compatible with the store as single source of truth, and it means the design must think in terms of "when do we republish" rather than "how does the page poll".

### 2.8 Can the page hand something back to the session? Yes, two ways.

VERIFIED, mechanism one, copy as prompt. From https://code.claude.com/docs/en/artifacts, a documented pattern:

> An artifact can act as a lightweight editor for a decision you then hand back to Claude. Ask for an export control that produces text you can paste into the terminal, so the result of interacting with the page flows back into the session instead of staying on the page.

The doc's own worked example is a triage board with draggable cards and a "Copy as prompt" button. That is close to exactly the handback the insight ledger design wants.

VERIFIED, mechanism two, the `downloads` capability. From the bundled `artifact-capabilities` skill and `downloads.d.ts` read in this session:

> The `downloads` capability lets a published page offer a generated file to the viewer: declare `capabilities: {downloads: true}`, then call `window.claude.downloads.save({filename, data})`. The viewer sees a confirmation and may decline, a save is never silent or guaranteed.

The type contract confirms: `save({filename, data})` where `data` is `string | Blob | ArrayBuffer | ArrayBufferView`, resolving to `status: "saved"`, rejecting with stable error codes including `bad_request` and `unavailable`. Frame code never downloads directly; the viewer must accept.

**Design instruction.** Handback is real but always human mediated, and always a round trip through the founder. There is no path from a button on the page back into the running session automatically. The two viable handback shapes are: (a) the page composes a prompt and the founder pastes it, (b) the page saves a file the founder points BrotherMode at. Both are honest and both keep the founder in the loop, which is what the complaint asks for anyway ("giving him the hand to take over").

### 2.9 Consent and the permission gate

VERIFIED. `Artifact` is marked `Permission required: Yes` in the tools reference table. The artifacts doc describes the prompt text shape:

> Before publishing a new artifact, Claude Code asks for permission; it might say something like `Claude wants to publish "Deploy failures by service" (deploy-failures.html) to a private page on claude.ai`.

VERIFIED, three independent kill switches exist, from https://code.claude.com/docs/en/artifacts and https://code.claude.com/docs/en/settings:

| Method | Setting |
| :-- | :-- |
| Settings file | `"disableArtifact": true` |
| Environment variable | `CLAUDE_CODE_DISABLE_ARTIFACT=1` |
| Permission rule | Add `Artifact` to `permissions.deny` |

VERIFIED, browser auto open is controllable: "To stop the browser from opening automatically when a new artifact is published, set `CLAUDE_CODE_ARTIFACT_AUTO_OPEN=0` in your environment."

VERIFIED, reopening: "Press `Ctrl+]` at any time to reopen the most recent artifact from the terminal."

**Design instruction.** The nothing-writes-before-consent rule is satisfied by construction for the first publish, because Claude Code gates it natively. But note that the doc also says Claude *writes the file into your project* before publishing: "Claude writes the page to an HTML or Markdown file in your project, then publishes it." That local write is a `Write` tool call and is NOT covered by the artifact permission prompt. BrotherMode's consent gate must therefore cover the file write, not rely on the publish prompt.

### 2.10 Availability gates that could silently kill the whole design

VERIFIED, the full requirement set from https://code.claude.com/docs/en/artifacts. Every one of these must hold or "Claude writes a local HTML file or says it cannot publish instead":

| Requirement | Condition |
| :-- | :-- |
| Plan | Pro, Max, Team, or Enterprise. On Enterprise, an Owner must enable it in claude.ai admin settings. On Team it is on by default. |
| Authentication | Session signed in with `/login`. Sessions using an API key, gateway token, or cloud provider credential **cannot publish**. |
| Model provider | Anthropic API only. Not on Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry. |
| Organization policy | CMEK, HIPAA, and Zero Data Retention must not be enabled. |
| Surface | Claude Code CLI 2.1.183 or later, or Claude desktop app 1.13576.0 or later. **Off by default in Agent SDK, GitHub Action, and MCP server contexts**, and when `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set. |

VERIFIED, one more networking gate: "The viewer on claude.ai loads each artifact from a sandboxed `*.claudeusercontent.com` origin. If your organization restricts outbound network access, add that domain to your allowlist alongside `claude.ai`."

**This is the biggest single risk to the whole visual surface plan.** A meaningful fraction of BrotherMode users, anyone on an API key, anyone on Bedrock or Vertex, anyone in a ZDR or HIPAA org, will get no artifact at all. The design must have a documented, non embarrassing fallback for those users, and BrotherMode should detect the failure rather than let the founder stare at a missing link. The fallback that already exists in the product (a static HTML explainer written to disk) is exactly the right degradation target, so the design should treat the local file as the primary artefact and the published page as an enhancement layered on top, not the other way round.

---

## 3. Inline widgets: not a Claude Code capability

**This is a correction to the brief.** The brief lists "can show inline widgets" as a given constraint. I could not confirm that for Claude Code, and the primary source points the other way.

VERIFIED from https://support.claude.com/en/articles/13979539-custom-visuals-in-chat-and-cowork, Anthropic's own help centre article on the feature:

> Claude can generate custom diagrams, charts, and interactive visuals directly in your conversation.

> Custom visuals are ephemeral by default. They live inline as part of Claude's response and aren't saved separately when the conversation moves on.

> Claude builds them using HTML, the same building blocks as web pages, so they're interactive and specific to your question rather than static images.

And, decisively, on where they work:

> Custom visuals work in chats on Claude web and desktop apps only. They don't render on Claude for iOS or Claude for Android.

Cowork is mentioned as a second supported surface, with the caveats that "Visuals don't render for others via a share link" and that they lack click to follow up interactivity there. **Claude Code is not named as a supported surface.** The article also states the feature is in beta with variable quality.

VERIFIED by omission, and I checked deliberately: I fetched the complete Claude Code documentation index at https://code.claude.com/docs/en/llms.txt and enumerated every page relating to UI, panels, preview, widgets, rendering or visual output. The list it returned contains artifacts, output styles, statusline, fullscreen rendering, interactive mode, context window, desktop, iOS simulator, agent view, Chrome, MCP, and channels. **There is no inline widget or custom visual page in the Claude Code documentation.**

Honest disclosure about my own session: I do have a tool named `mcp__visualize__show_widget` whose description says it renders SVG or HTML inline alongside the text response, with a `sendPrompt(text)` global available for sending a message back to chat. That is an **MCP server**, not a Claude Code native capability, and it is not something a BrotherMode plugin can count on being present. If the founder is working in Claude Cowork or the Claude desktop Chat tab rather than the Claude Code CLI, inline widgets may be available to them there. That is a question about the founder's actual working surface, not about what BrotherMode can ship.

**Design instruction.** Do not design the primary experience around inline widgets. If the founder wants in chat visuals, that is a request to change which Claude surface he works in, and it should be surfaced to him as such rather than silently assumed.

### Artifact versus inline widget, summarised

| | Artifact | Inline widget / custom visual |
| :-- | :-- | :-- |
| Documented in Claude Code | Yes, https://code.claude.com/docs/en/artifacts | **No** |
| Where it renders | Separate browser page on claude.ai | Inline in the chat response |
| Persistence | Persistent, versioned, shareable | "Ephemeral by default... aren't saved separately" |
| Updatable in place | Yes, same URL, live refresh | Not documented |
| Addressable by a plugin | Yes, via a skill that instructs the Artifact tool | Not applicable |
| Status | Generally available, beta per the June 2026 blog post for Team/Enterprise | Beta, "variable quality" |

---

## 4. What a plugin can ship, and which parts can put something visual in front of a user

VERIFIED from https://code.claude.com/docs/en/plugins, the plugin directory table, quoted:

| Directory | Location | Purpose |
| :-- | :-- | :-- |
| `.claude-plugin/` | Plugin root | Contains `plugin.json` manifest |
| `skills/` | Plugin root | Skills as `<name>/SKILL.md` directories |
| `commands/` | Plugin root | Skills as flat Markdown files. Use `skills/` for new plugins |
| `agents/` | Plugin root | Custom agent definitions |
| `hooks/` | Plugin root | Event handlers in `hooks.json` |
| `.mcp.json` | Plugin root | MCP server configurations |
| `.lsp.json` | Plugin root | LSP server configurations for code intelligence |
| `monitors/` | Plugin root | Background monitor configurations in `monitors.json` |
| `bin/` | Plugin root | Executables added to the Bash tool's `PATH` while the plugin is enabled |
| `settings.json` | Plugin root | Default settings applied when the plugin is enabled |

Plus, VERIFIED from https://code.claude.com/docs/en/output-styles: "Plugins can also ship output styles in an `output-styles/` directory."

Now, component by component, can it put something visual in front of the founder:

**skills/ (and commands/): YES, this is the lever.** A skill is a prompt that loads into the conversation and drives Claude's tools. Since `Artifact` is a tool Claude holds, a skill can instruct a publish. The artifacts doc says this explicitly in its Related resources: "Turn an artifact prompt you reuse into a skill so you can invoke it as a command." VERIFIED. This is the sanctioned path: `/brothermode:status` becomes "regenerate the project view from the store and republish it to the stored URL".

Useful skill frontmatter, VERIFIED from https://code.claude.com/docs/en/skills:

- `disable-model-invocation: true` restricts a skill to user invocation only. Recommended by the doc "for workflows with side effects or that you want to control timing".
- `allowed-tools` pre approves tools for the turn that invokes the skill, and the grant "clears when you send your next message". A skill that wants to publish without a second prompt could list `Artifact` here, though for a consent sensitive product that is a deliberate choice, not a default.
- `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` are substituted in both the skill body and in Bash rules in `allowed-tools`, so a skill can run a bundled generator script without prompting. Requires v2.1.129 or later. The doc's own worked example is literally a chart renderer:

  > ```
  > name: render-chart
  > description: Render a chart from a CSV file
  > allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)
  > ```

- `context: fork` runs a skill in its own subagent, in the background by default, with the result arriving in the conversation when it completes. Useful for "regenerate the whole view" without eating the main thread.
- Skill content persists: "the rendered `SKILL.md` content enters the conversation as a single message and stays there for the rest of the session". So a skill's instructions are standing instructions, which is the right way to encode "keep the project view current".

VERIFIED, and directly on point for a standard library Python product, from the skills doc:

> Skills can bundle and run scripts in any language, giving Claude capabilities beyond what's possible in a single prompt. One powerful pattern is generating visual output: interactive HTML files that open in your browser for exploring data, debugging, or creating reports.

The same doc mentions a "Review viewer" that "opens an HTML report where you inspect each output and record qualitative feedback that the next iteration reads". So Anthropic's own guidance already blesses the generate-HTML-from-a-script pattern.

**hooks/: partially, see section 5.**

**monitors/: indirectly, and this is the freshness engine.** VERIFIED from https://code.claude.com/docs/en/plugins-reference:

> Plugins can declare background monitors that Claude Code starts automatically when the plugin is active. Each monitor runs a shell command for the lifetime of the session and delivers every stdout line to Claude as a notification, so Claude can react to log entries, status changes, or polled events without being asked to start the watch itself.

Schema, verbatim from the reference:

```json
[
  {
    "name": "deploy-status",
    "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/poll-deploy.sh",
    "description": "Deployment status changes"
  },
  {
    "name": "error-log",
    "command": "tail -F ./logs/error.log",
    "description": "Application error log",
    "when": "on-skill-invoke:debug"
  }
]
```

Constraints, VERIFIED: monitors are an **experimental component**, they "run only in interactive CLI sessions, run unsandboxed at the same trust level as hooks, and are skipped on hosts where the Monitor tool is unavailable". They share the `Monitor` tool's availability.

**Design use.** A monitor polling the SQLite store for a change counter is the cleanest documented way to get "the store changed, Claude, republish the view" without a daemon and without polling from inside the artifact. It is standard library Python compatible: the monitor command is just a script that prints a line. But it is experimental and interactive CLI only, so it must be an enhancement, never load bearing.

**.mcp.json: no direct visual output.** See section 6.

**settings.json in a plugin: almost no visual reach.** VERIFIED from https://code.claude.com/docs/en/plugins: "Currently, only the `agent` and `subagentStatusLine` keys are supported." So a plugin **cannot** ship the main `statusLine`. It can ship `subagentStatusLine`. Cross checked against https://code.claude.com/docs/en/settings, which documents `statusLine` and `subagentStatusLine` as user configurable template keys, and gives no plugin path for `statusLine`.

**output-styles/: yes, but it changes prose, not pixels.** VERIFIED: "Output styles change how Claude responds, not what Claude knows. They modify the system prompt to set role, tone, and output format." A plugin output style can carry `force-for-plugin: true`, which "applies this style automatically whenever the plugin is enabled, without requiring users to select it. Overrides the user's `outputStyle` setting." The docs' own example style is literally "Diagrams first: Lead every explanation with a diagram", instructing Mermaid use in responses. Note the built in **Explanatory** style "provides educational 'Insights' in between helping you complete software engineering tasks" and **Learning** adds `TODO(human)` markers for the user to implement, which is a shipped precedent for exactly the insight-box and hand-the-user-the-wheel behaviours the founder is asking for.

Caveat, VERIFIED: "Output style is part of the system prompt, which Claude Code reads once at session start. Changes take effect after `/clear` or a new session." And styles do not apply to subagents.

**bin/: yes, as plumbing.** Executables in `bin/` land on the Bash tool's `PATH` while the plugin is enabled. A `brothermode-render` command that reads the store and emits HTML would live here.

---

## 5. Hooks: which fire, and can any trigger a visual update

VERIFIED, the complete hook event list from https://code.claude.com/docs/en/hooks:

`SessionStart`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `Elicitation`, `ElicitationResult`, `SessionEnd`.

Notable ones for this design, verbatim:

- `SessionStart`: "When a session begins or resumes"
- `FileChanged`: "When a watched file changes on disk. The `matcher` field specifies which filenames to watch"
- `TaskCreated` / `TaskCompleted`: "When a task is being created via `TaskCreate`" / "When a task is being marked as completed"
- `Stop`: "When Claude finishes responding"
- `MessageDisplay`: "While assistant message text is displayed"
- `SessionEnd`: "When a session terminates"

VERIFIED, the JSON output schema universal fields:

| Field | Description |
| :-- | :-- |
| `continue` | If `false`, Claude stops processing entirely after the hook runs |
| `stopReason` | Message shown to the user when `continue` is `false`. Not shown to Claude |
| `suppressOutput` | If `true`, hides the hook's stdout from the transcript |
| `systemMessage` | Warning message shown to the user |
| `terminalSequence` | A terminal escape sequence for Claude Code to emit on your behalf, such as a desktop notification, window title, or bell |
| `decision` | allow/block for certain events |
| `reason` | Explanation accompanying a block |
| `hookSpecificOutput` | Event specific object with fields including `hookEventName`, `permissionDecision`, `additionalContext`, `updatedInput`, `updatedToolOutput`, `worktreePath`, `action`, `content`, `displayContent`, and `retry` |

### Can a hook trigger a visual update?

**Not directly. VERIFIED negative.** A hook is a shell command. It has no access to Claude's tools, so no hook can call `Artifact`. Nothing in the hooks documentation offers a way to publish, render, or open a page.

**Indirectly, three real paths. INFERRED, composition shown.**

1. **A hook can regenerate the file.** Verified premise A: hooks run arbitrary shell commands with the event payload on stdin. Verified premise B: an artifact is published from an HTML or Markdown file in the project. Composition: a `PostToolUse` or `FileChanged` or `Stop` hook can run a standard library Python script that reads the SQLite store and rewrites `PROJECT-VIEW.html` on disk. What it cannot do is publish that file. INFERRED, high confidence.

2. **A hook can ask Claude to republish.** Verified premise: `hookSpecificOutput.additionalContext` is shown to Claude for `SessionStart`, `Setup`, `SubagentStart`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Stop`, and `SubagentStop`. Composition: a hook that detects a store change can inject "the project view is stale, republish `PROJECT-VIEW.html` to <stored URL>" as context, and Claude, holding the `Artifact` tool, does it. INFERRED, high confidence, but note this is a *request*, not a guarantee: Claude decides. Do not treat republish as deterministic.

3. **A hook can raise a native alert without any model involvement.** Verified: `systemMessage` is a "Warning message shown to the user", and `terminalSequence` emits "a terminal escape sequence for Claude Code to emit on your behalf, such as a desktop notification, window title, or bell". Composition: a key alert (a fence violation, a failing gate, a decision needed) can reach the founder as a native warning plus a desktop notification, deterministically, with zero model tokens. INFERRED for the composition, VERIFIED for both premises. This is the cheapest and most reliable "key alert" channel in the whole harness and it is currently unused by BrotherMode.

4. **`MessageDisplay` can rewrite what appears on screen.** VERIFIED: the doc's user visible output summary states "`MessageDisplay`: custom display via `displayContent` replaces on-screen text". This is the only documented hook that alters rendered output. UNVERIFIED whether `displayContent` accepts anything beyond text (ANSI, box drawing); I did not find a schema for its content type. Worth a targeted experiment before designing recurrent insight boxes on top of it.

**Design instruction.** Hooks are the *trigger* and *alert* layer. Artifacts are the *render* layer. Skills are the *bridge*. Keep those roles separate and the design stays inside what the harness actually does.

---

## 6. Native panels, side surfaces, and preview capability

I enumerated these from the documentation index rather than guessing.

**Claude Code CLI, terminal.** VERIFIED from https://code.claude.com/docs/en/fullscreen: fullscreen rendering "draws the interface on the terminal's alternate screen buffer, like `vim` or `htop`" and adds mouse support: click to position the cursor, click a `/` command or `@` file suggestion, click a select menu option, click a multi select option and its submit button, click a collapsed tool result to expand it, `Cmd`/`Ctrl` click a URL or file path to open it, click and drag to select, wheel to scroll. Default renderer for anyone who first used Claude Code on or after 6 May 2026; `/tui fullscreen` and `/tui default` switch.

**But there is no plugin API for it.** VERIFIED negative: nothing in the fullscreen, interactive mode, plugins, or plugins reference documentation exposes a pane, region, buffer, or draw call to a plugin. The interface Claude Code draws is Claude Code's; a plugin contributes prompts, hooks, tools and scripts, never widgets. A plugin cannot open a split, cannot own a region, cannot render a chart into the transcript.

**Native dialogs Claude Code draws, which a plugin can cause indirectly:**

- `AskUserQuestion`. VERIFIED from the tools reference: "Asks multiple-choice questions to gather requirements or clarify ambiguity. Questions stay open until you answer them by default." Answer by picking an option, or typing your own through the `Other` row or the notes field. Under fullscreen these are mouse clickable. `askUserQuestionTimeout` (default `"never"`, accepts `"60s"`, `"5m"`, `"10m"`) makes an unanswered question auto continue. This is the founder gate mechanism and it is already a real, native, non prose UI.
- `ReportFindings`. VERIFIED from the tools reference: "Reports code-review findings as a structured list, with a file, summary, and failure scenario per finding, **so Claude Code can render them instead of printing them as text**." Requires v2.1.196 or later; as of v2.1.199 a finding can carry a `category` slug "shown next to the file location in the rendered list". **This is the closest thing in the harness to a native, structured insight box**, and it is a first class rendered list rather than prose. It is scoped to code review by its description, and the doc says "Claude calls it when active code-review instructions tell it to". Whether BrotherMode can legitimately drive it for non review findings is UNVERIFIED and worth testing.
- `ExitPlanMode`. VERIFIED: "Presents a plan for approval and exits plan mode." A native approval surface.
- MCP elicitation dialogs. VERIFIED from https://code.claude.com/docs/en/mcp: "MCP servers can request structured input from you mid-task using elicitation. When a server needs information it can't get on its own, Claude Code displays an interactive dialog and passes your response back to the server. No configuration is required on your side."

**Status line.** VERIFIED from https://code.claude.com/docs/en/statusline: "a customizable bar at the bottom of Claude Code that runs any shell script you configure. It receives JSON session data on stdin and displays whatever your script prints". It "renders in its own row above the built-in footer badges and does not replace them". Formatting supported: multiple lines, ANSI colour escape codes, and OSC 8 escape sequences to make text clickable (`Cmd`click on macOS, `Ctrl`click elsewhere) on terminals like iTerm2, Kitty or WezTerm. Update model: event driven, debounced at 300ms, with an optional `refreshInterval` in seconds (minimum 1) to re run on a timer, needed because "The event-driven triggers can go quiet when the main session is idle".

The stdin payload is rich: `model.*`, `cwd`, `workspace.*` (including `git_worktree` and parsed `repo.host/owner/name`), `cost.total_cost_usd`, `cost.total_lines_added/removed`, `context_window.used_percentage` and `remaining_percentage`, `rate_limits.five_hour/seven_day.used_percentage` and `resets_at`, `session_id`, `session_name`, `transcript_path`, `version`, `output_style.name`, `agent.name`, `pr.number/url/review_state`, `worktree.*`. VERIFIED, read from the field table.

**But a plugin cannot install it.** VERIFIED: plugin `settings.json` supports "only the `agent` and `subagentStatusLine` keys". BrotherMode can ship a status line *script* and a documented one line instruction, or offer to write the user's settings after consent, but it cannot ship it silently. That is arguably correct behaviour for a consent first product.

**Footer link badges.** VERIFIED from https://code.claude.com/docs/en/settings: `footerLinksRegexes` is an "Array of regex patterns; matching text in Claude Code output becomes clickable links", each with a `pattern`, a `url` template with `$1`/`$2` capture group placeholders, and an optional `label`. Requires v2.1.181 or later. This is a documented, zero script way to make BrotherMode identifiers (a run id, a decision id, an artifact id) clickable in the terminal. It is a user setting, not a plugin setting.

**Claude Code Desktop.** VERIFIED from the doc index description at https://code.claude.com/docs/en/desktop: the Code tab offers "parallel sessions with Git isolation, drag-and-drop pane layout, integrated terminal and file editor, side chats, computer use, Dispatch sessions from your phone, visual diff review, app previews, PR monitoring, connectors". There is also an iOS Simulator pane (https://code.claude.com/docs/en/desktop-ios-simulator) and an agent view for managing many sessions (https://code.claude.com/docs/en/agent-view). UNVERIFIED whether any of these panes is addressable by a plugin; I found no plugin API for them and the desktop page is written for end users, not extension authors. Treat desktop panes as founder conveniences, not as a BrotherMode target.

**Reaching the founder when he is away.** VERIFIED from the tools reference:

- `PushNotification`: "Sends a desktop notification, and a phone push when Remote Control is connected, so a long-running task or scheduled task can reach you when you step away."
- `SendUserFile`: "Sends files from the session to you with an optional caption, so a generated report, diagram, screenshot, or built artifact reaches your device instead of only being mentioned in the transcript. As of v2.1.196, the optional `display` input controls presentation: `render` opens the file inline in the client, `attach` shows a download card only, and when unset the client decides by file type. **Available when a Remote Control client is connected or the session runs in a managed cloud environment** such as Claude Code on the web."

`SendUserFile` with `display: "render"` is a genuinely interesting second render path, but note the availability gate: it needs Remote Control connected or a managed cloud session. Not available in a plain local terminal session with no Remote Control. VERIFIED.

**Channels.** VERIFIED from https://code.claude.com/docs/en/channels: an MCP server can push events into a running session, so CI results, webhooks and chat messages arrive while the founder is away. Research preview, requires `--channels` at startup, requires Bun for the official plugins, blocked by default for Team and Enterprise until an Owner enables it. Not a visual surface, but it is the documented way an external event reaches a live session, which could drive a republish. Too many gates to be load bearing.

**MCP as a visual surface: no.** VERIFIED from https://code.claude.com/docs/en/mcp. What an MCP server can surface is tools, prompts, resources (referenced with `@` mentions), elicitation dialogs, and image content in tool results (subject to `MAX_MCP_OUTPUT_TOKENS`, default warning at 10,000 tokens and a 25,000 token cap). Images returned by MCP tools go to the model, not to a rendered pane. There is no documented MCP UI surface in Claude Code. And BrotherMode is standard library Python with no dependencies and no daemon, so shipping an MCP server is against its own constraints anyway.

**Images in the terminal: no.** VERIFIED from the tools reference Read tool behaviour: "PNG, JPG, and other image formats are returned as **visual content that Claude can see**, not as raw bytes." That is the model seeing the image, not the founder. Nothing in the documentation renders an image into the terminal for the user.

---

## 7. Practical limits, consolidated

| Limit | Value | Status |
| :-- | :-- | :-- |
| Artifact rendered size | 16 MiB or smaller | VERIFIED, artifacts doc |
| Artifact file types | `.html`, `.htm`, `.md` | VERIFIED, artifacts doc |
| Artifact network | No external requests at all, CSP blocks scripts, styles, fonts, images, `fetch`, XHR, WebSocket | VERIFIED, artifacts doc |
| Artifact backend | None. No form storage, no auth, no API | VERIFIED, artifacts doc |
| Artifact routes | Single page. Relative links do not resolve | VERIFIED, artifacts doc |
| Artifact state | No storage capability in Claude Code. Roster is `downloads` and `mcp` only | VERIFIED, `artifact-capabilities` skill, this session |
| Artifact live data | MCP connectors only, requires v2.1.209+, claude.ai connectors only, local MCP servers excluded | VERIFIED, artifacts doc |
| Artifact token cost | "a styled page is more token-intensive than the same content as terminal text"; inline CSS, JS and data URI images are the main contributors | VERIFIED, artifacts doc |
| Artifact cross session update | Requires passing the stored URL, else a new artifact is created | VERIFIED, artifacts doc |
| Status line update | Event driven, 300ms debounce, optional `refreshInterval` in whole seconds, minimum 1 | VERIFIED, statusline doc |
| Status line formatting | Multi line, ANSI colours, OSC 8 clickable links on supporting terminals | VERIFIED, statusline doc |
| Plugin `settings.json` | Only `agent` and `subagentStatusLine` keys supported | VERIFIED, plugins doc |
| Monitors | Experimental, interactive CLI sessions only, unsandboxed at hook trust level | VERIFIED, plugins reference |
| Output style change | Takes effect only after `/clear` or a new session; does not apply to subagents | VERIFIED, output styles doc |
| MCP tool output | Warning above 10,000 tokens, 25,000 token default cap, raise with `MAX_MCP_OUTPUT_TOKENS` | VERIFIED, mcp doc |
| `SendUserFile` | Needs Remote Control connected or a managed cloud session | VERIFIED, tools reference |

---

## 8. Verification ledger

| Capability | Verdict | Evidence |
| :-- | :-- | :-- |
| Artifact exists as a built in Claude Code tool named `Artifact` | VERIFIED | tools-reference table row; `permissions.deny` accepts `Artifact` |
| Artifact is self contained, strict CSP, no external requests | VERIFIED | artifacts doc Page constraints table |
| Artifact supports inline JS and full interactivity | VERIFIED | artifacts doc: "anything you can express in HTML, CSS, and inline JavaScript is in scope" |
| Artifact renders mermaid | **UNCONFIRMED for the CLI** | Stated in the `Artifact` tool description in this session; absent from artifacts doc, absent from the entire bundled skills payload, absent from a domain restricted web search |
| Artifact is theme aware via `prefers-color-scheme` plus `data-theme` | VERIFIED (in product source) | bundled `artifact-design` skill, this session. Not on code.claude.com |
| Artifact adopts a project design system from CLAUDE.md | VERIFIED | artifacts doc, Improve the visual design section, with the exact block format |
| Artifact updates in place at the same URL, live for open viewers | VERIFIED | artifacts doc; blog post |
| Updating from a new session requires the stored URL | VERIFIED | artifacts doc |
| Artifact can hold state | **VERIFIED NEGATIVE for Claude Code** | artifacts doc "No backend"; capability roster is `downloads` and `mcp` only. Diverges from claude.ai chat artifacts, which do document storage |
| Artifact can fetch data at view time | VERIFIED, narrowly | Only claude.ai MCP connectors, only v2.1.209+, local MCP servers explicitly excluded. This machine is 2.1.207 |
| Artifact can hand a result back to the session | VERIFIED | "Copy as prompt" pattern in artifacts doc; `downloads` capability with `window.claude.downloads.save` |
| First publish is permission gated, republish is not | VERIFIED | artifacts doc; tools-reference `Permission required: Yes` |
| Artifacts can be silently unavailable (plan, API key, Bedrock/Vertex, ZDR, HIPAA, SDK) | VERIFIED | artifacts doc Availability table |
| Inline widgets exist in Claude Code | **VERIFIED NEGATIVE** | Support article scopes custom visuals to "chats on Claude web and desktop apps only" plus Cowork; no such page exists in the Claude Code docs index |
| A plugin can ship skills, agents, hooks, MCP servers, LSP servers, monitors, `bin/`, output styles, limited settings | VERIFIED | plugins doc directory table; output-styles doc |
| A skill can drive an artifact publish | VERIFIED | artifacts doc Related resources: "Turn an artifact prompt you reuse into a skill" |
| A skill can run a bundled script without a permission prompt | VERIFIED | skills doc `${CLAUDE_SKILL_DIR}` in `allowed-tools`, v2.1.129+; the doc's own example is a chart renderer |
| A hook can call the Artifact tool | **VERIFIED NEGATIVE** | Hooks are shell commands; no tool access documented anywhere in the hooks page |
| A hook can regenerate an HTML file on disk | INFERRED (high confidence) | Hooks run arbitrary shell commands; artifacts publish from a project file |
| A hook can ask Claude to republish via `additionalContext` | INFERRED (high confidence, but non deterministic) | `additionalContext` is shown to Claude on 11 named events; Claude holds the tool |
| A hook can raise a native alert and a desktop notification with no model involvement | INFERRED (both premises verified) | `systemMessage` is "shown to the user"; `terminalSequence` emits "a desktop notification, window title, or bell" |
| `MessageDisplay` `displayContent` replaces on screen text | VERIFIED that it does; UNVERIFIED what content types it accepts | hooks doc user visible output summary |
| `ReportFindings` renders a structured list natively | VERIFIED it exists and renders; UNVERIFIED whether it can be driven outside code review | tools-reference row, v2.1.196+, `category` slug from v2.1.199 |
| `AskUserQuestion` is a native, mouse clickable, non prose decision UI | VERIFIED | tools-reference behaviour section; fullscreen doc multi select clicking, v2.1.208+ |
| A plugin can install the main status line | **VERIFIED NEGATIVE** | plugins doc: "only the `agent` and `subagentStatusLine` keys are supported" |
| Status line supports colour, multiple lines and clickable links | VERIFIED | statusline doc |
| `footerLinksRegexes` makes matched output text clickable | VERIFIED | settings doc, v2.1.181+ |
| Claude Code has a plugin addressable panel or preview pane | **VERIFIED NEGATIVE** for the CLI; UNVERIFIED for Desktop | No such API in plugins, plugins-reference, fullscreen or interactive-mode; desktop panes documented for users only |
| MCP can render a UI in Claude Code | **VERIFIED NEGATIVE** | mcp doc exposes tools, prompts, resources, elicitation dialogs, and image content to the model. No UI surface |
| Claude Code renders images to the user in the terminal | **VERIFIED NEGATIVE** | Read returns images "as visual content that Claude can see" |

---

## 9. What this means against the BrotherMode constraints

**"Runs inside Claude Code, which can render Artifacts."** Correct, and the artifact is the whole visual story. Budget for it: the doc warns that a styled page costs meaningfully more output tokens than the same content as terminal text, and names data URI images as the worst offender. Prefer SVG and CSS over raster. The doc says so directly.

**"Can show inline widgets."** Not established for Claude Code. Treat this constraint as withdrawn until the founder's actual surface is confirmed. If he is in Cowork or the Chat tab, revisit.

**"Standard library Python only, no dependencies, no daemon, no server."** Fully compatible. A Python script writes an HTML file with inlined CSS and JS; the Artifact tool publishes it. Nothing needs to serve anything, because the CSP forbids the page from talking to a server anyway. The no-daemon rule is satisfied because freshness comes from republishing on events, not from a background process.

**"The store is the single source of truth, any view is GENERATED from rows."** Not just compatible, enforced by the platform: the artifact literally cannot store anything, so there is no way to accidentally let the view become authoritative. Design the renderer as a pure function from rows to HTML.

**"Nothing may write before setup consent."** Two gates, and only one is free. The `Artifact` publish is natively permission gated on first publish. The *file write* that precedes it is not covered by that prompt, so BrotherMode's own consent gate must cover the write. Also note republishing never prompts again, so once consent is given the live view updates silently, which is the desired behaviour but must be disclosed at consent time.

**"The founder cannot read logs and should never have to."** The strongest unused lever here is the hook `systemMessage` plus `terminalSequence` pair: a deterministic, model free, native warning and desktop notification for key alerts. That reaches him without prose and without logs. Pair it with `footerLinksRegexes` so any BrotherMode identifier in the transcript becomes a click into the live view.

**On the designed but unbuilt insight ledger and handback.** The half hour briefing maps cleanly onto a republished artifact with an in page timeline. The handback maps onto the two verified handback mechanisms: a "Copy as prompt" control (Anthropic's own documented pattern), or `window.claude.downloads.save` under the `downloads` capability. Neither closes the loop automatically, which is fine, because the founder taking the wheel is the point.

---

## 10. What I could not check, and what should be tested before the design is finalised

Stated plainly, per the closing disclosure rule.

1. **Mermaid rendering in an artifact.** The only claim comes from a tool description in my session. The definitive test is to publish one artifact containing both a ```mermaid fence and a `<pre class="mermaid">` block and look at it. I did not run that test: publishing is a content publication action and I am a subagent with no route to the founder's consent. This is the single highest value five minute experiment remaining.

2. **Whether `ReportFindings` can be driven outside code review.** It is the only native structured-list renderer in the harness and would be a genuine insight box if it generalises. Its documented trigger is "when active code-review instructions tell it to". Untested.

3. **What content `MessageDisplay.displayContent` accepts.** Text is confirmed. Whether ANSI, box drawing or anything richer survives is unknown, and it is the only hook that alters rendered output.

4. **The founder's actual plan, auth method and provider.** Artifacts silently degrade to a local file on an API key, on Bedrock, Vertex or Foundry, under ZDR or HIPAA, or below a Pro plan. I have no visibility into which of these applies. This gates the entire design and should be checked first, not last.

5. **Claude Code Desktop pane addressability.** I found no plugin API and the desktop documentation is written for end users. I did not fetch the desktop page in full (it exceeded the fetch limit and was persisted rather than read end to end), so a plugin hook into app previews or visual diff review may exist and be undocumented in the pages I read. Treat as unknown rather than absent.

6. **Version skew on this machine.** `claude --version` reports 2.1.207 while the bundled skills payload is 2.1.219. I did not chase why. It matters only insofar as 2.1.207 is below the 2.1.209 floor for artifact connector calls, which the design does not rely on anyway.

7. **Pages read only in part.** The desktop, interactive mode, statusline, skills, tools reference, MCP and plugins reference pages each exceeded the fetch size limit and were persisted to disk; I read the relevant sections by targeted search rather than end to end. I may have missed a capability that no keyword I chose would surface. The pages read completely are artifacts, output styles, fullscreen, channels, plugins, hooks, and both support articles.

8. **No claim here rests on a single source where a second was available.** Artifact behaviour is corroborated across the artifacts doc, the tools reference, the settings page and the launch blog. The inline widget negative rests on the support article plus the absence of any such page in the full documentation index, which is two independent kinds of evidence but both from Anthropic. Mermaid rests on one source and is labelled accordingly.
