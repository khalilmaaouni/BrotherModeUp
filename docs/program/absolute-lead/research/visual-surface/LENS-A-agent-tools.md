# LENS A: how the best AI coding and agent tools show a non expert what the agent is doing

Research input for the BrotherMode visual surface design. Written 2026-08-05.

Scope: what the user SEES while the agent works, how a plan or task list is surfaced, how decisions and alternatives are shown, how the user takes over, and what makes it comprehensible to someone who cannot read code. Ends with the transferable patterns and the patterns that would be WRONG for BrotherMode.

Every behavioural claim below is tied to a page I actually fetched and read, with the URL. Where a claim is second hand or I could not confirm it, it is marked UNVERIFIED in place.

---

## 0. Source ledger

Pages fetched and read for this report:

| Product | Primary pages read |
| --- | --- |
| GitHub Copilot Workspace | https://raw.githubusercontent.com/githubnext/copilot-workspace-user-manual/main/overview.md , https://github.blog/news-insights/product-news/github-copilot-workspace/ , https://raw.githubusercontent.com/githubnext/copilot-workspace-user-manual/main/README.md |
| GitHub Copilot coding agent | https://docs.github.com/en/copilot/how-tos/agents/coding-agent/track-copilot-sessions , https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent |
| Devin | https://docs.devin.ai/ , https://docs.devin.ai/get-started/devin-intro , https://docs.devin.ai/work-with-devin/devin-session-tools , https://docs.devin.ai/essential-guidelines/instructing-devin-effectively |
| Cursor | https://cursor.com/docs/agent/planning , https://cursor.com/docs/agent/review |
| Replit Agent | https://docs.replit.com/replitai/agent , https://docs.replit.com/features/agent/plan-mode.md , https://docs.replit.com/features/agent/overview.md , https://docs.replit.com/features/agent/app-testing.md , https://docs.replit.com/features/version-control/checkpoints-and-rollbacks.md , https://docs.replit.com/learn/build-with-agent.md , https://docs.replit.com/llms.txt |
| Lovable | https://docs.lovable.dev/features/plan-mode , https://docs.lovable.dev/features/agent-mode , https://docs.lovable.dev/features/projects/history , https://docs.lovable.dev/features/projects/editor , https://docs.lovable.dev/features/visual-edit (resolves to the preview toolbar page) , https://docs.lovable.dev/llms.txt |
| Bolt | https://support.bolt.new/best-practices/plan-mode , https://support.bolt.new/ |
| v0 | https://v0.app/docs , https://v0.app/docs/introduction |
| Claude Code | https://code.claude.com/docs/en/agent-view , https://code.claude.com/docs/en/permission-modes , https://code.claude.com/docs/en/checkpointing , https://code.claude.com/docs/en/tools-reference , https://code.claude.com/docs/en/common-workflows , https://code.claude.com/docs/en/commands.md |
| Kiro (added: closest shipped analogue to a generated project brief) | https://kiro.dev/docs/specs/ , https://kiro.dev/docs/specs/feature-specs/ |
| Google Jules (added: plan approval and diff rendering) | https://jules.google/docs , https://jules.google/docs/changelog/ |
| OpenAI Codex cloud (added: the asynchronous delegation contract) | https://learn.chatgpt.com/docs/cloud |

Verified by direct API call rather than by a page: the GitHub Copilot Workspace user manual repository is archived. `gh api repos/githubnext/copilot-workspace-user-manual` returns `"archived": true` with `"pushed_at": "2025-09-02T00:30:50Z"`.

UNVERIFIED: the exact date the Copilot Workspace technical preview was sunset. Search results repeatedly assert 2025-05-30 and assert the workflow was folded into Copilot coding agent, but I did not open a GitHub changelog or GitHub Next page stating it, so I am not asserting the date. What IS verified is that the manual repo is archived and that a separate, pull request centric Copilot coding agent is documented and current on docs.github.com.

---

## 1. GitHub Copilot Workspace

The most explicit "make the machine's reasoning editable" surface anyone has shipped, and the most useful single reference for BrotherMode even though the standalone product did not survive.

**What the user sees.** Four named stages, in order, each with its own visible artifact. From the user manual:

1. **Task**: a natural language description of intent, seeded from a GitHub issue including "the title and body of the issue, plus the issue's comment thread".
2. **Specification**: three parts, a topic (a distilled question posed against the codebase), a current specification described as "a bulleted list describing the current behavior of the codebase", and a proposed specification, "a bulleted list which articulates the state that the codebase would be in after resolving the task".
3. **Plan**: "A list of the files that need to be modified ... in order to accomplish the success criteria", each file carrying "specific steps that indicate the exact changes that need to be made".
4. **Implementation**: generated file contents shown as diff views with per file progress indicators.

**Plan surfacing.** The plan is not prose. It is a file list with per file steps, generated from the spec, shown as a structure the user can attack.

**Decisions and alternatives.** Editability is the alternatives mechanism. Of the spec: "You can easily edit/delete steps from the current spec, or even choose to regenerate an entirely new spec." Of the plan: "The plan is fully editable and regeneratable, which allows you to refine and steer Copilot Workspace." The announcement generalises it: "Everything that GitHub Copilot Workspace proposes, from the plan to the code, is fully editable, allowing you to iterate until you're confident in the path ahead."

**Take over.** Two exits: edit the diffs in place ("The diff editors are editable, which allows making minor tweaks directly to the code"), or leave for a full environment, per the announcement, "jump into the underlying GitHub Codespace, and tweak all code changes until you are happy with the final result".

**Why a non coder can follow it.** The current versus proposed specification pair is the strongest single device in this whole survey. It states, in bullets and in English, what the system does today and what it will do after, before any code exists. A person who cannot read a diff can still read those two lists and say "no, that is not what I meant". The announcement is explicit about the audience: it aims to "materially lower the barrier of entry for who can build software".

**The cautionary half.** The standalone product is gone (manual repo archived, verified above) and the durable successor is anchored to artifacts GitHub already had: issues, pull requests, commits, logs. That is a design signal, taken up as T14 below.

---

## 2. GitHub Copilot coding agent (the successor surface)

**What the user sees.** An agents panel "available from any page on GitHub", and per session a session log. The user can "monitor the agent's progress, token usage, and session length", and session logs "show Copilot's internal reasoning and the tools it used to understand your repository, make changes, and validate its work".

**Plan surfacing.** There is no separate plan artifact of the Copilot Workspace kind on this surface. The unit of work is the pull request, and progress is commits landing on it: "With Copilot cloud agent, all coding and iterating happens on GitHub", and "Working on GitHub adds transparency, with every step happening in a commit and being viewable in logs." The user's job is that "You can review the diff, iterate, and create a pull request when you're ready." Hard stop: "Each Copilot cloud agent session has a maximum execution time of 59 minutes."

**Decisions and alternatives.** Not surfaced as options. Reasoning is surfaced as log text after the fact.

**Take over.** Steering mid flight through a prompt input in the session log viewer, with the docs giving a worked example of a steering message ("Use our existing ErrorHandler utility class instead of writing custom try-catch blocks for each endpoint"), and after the fact through a normal pull request.

**Why a non coder can follow it.** Honestly, poorly. This is the log reading model, and it is precisely the model the founder is rejecting. The one genuinely non expert friendly feature is traceability: "Each commit message includes a link to the session logs, so you can trace why a change was made during code review or an audit." One click from a change to the reason for the change is the pattern worth stealing.

---

## 3. Devin

**What the user sees.** A conversational panel plus a workspace of live developer tools. Per the intro page, "Devin is designed to be a conversational user interface, and allows you to follow and take over Devin's development process in the embedded IDE." The tools, per the session tools page:

- **Shell**: "Devin's terminal, where you can watch commands being executed and view output logs", showing "every command Devin has executed during the session" with output previews, and clicking a command jumps to that point in time.
- **IDE**: VS Code loaded with the repositories, where the user can "take over Devin's work when necessary, test and fix changes end-to-end without leaving the Devin webapp".
- **Interactive Browser** (under a Desktop tab): useful for "browser tasks where Devin may require assistance, such as completing CAPTCHAs, completing multi-factor authentication steps".
- **Progress tab**: a chronological consolidation of every shell command, code edit, and browser interaction, where the user clicks an individual step to see its detail in context.

**Plan surfacing.** The Progress tab is a step timeline, and the docs note the tools are reachable "by clicking any progress steps in the session". I fetched the instructing-Devin page looking for a named plan artifact or a confidence signal and found neither. UNVERIFIED: whether Devin exposes a pre execution, editable plan artifact or an explicit confidence score in the current product.

**Take over.** Explicit and physical: the user stops the session, which makes the IDE and the terminals writable, and then types.

**Why a non coder can follow it.** It mostly cannot. Three of the four surfaces are a terminal, an IDE, and a browser. The transferable idea is not the panes, it is the Progress tab: one chronological list of steps where each step is clickable and expands to its own evidence.

---

## 4. Cursor

**What the user sees while it works.** "The diff view shows changes as they happen", explicitly so the engineer can stop the agent if it is heading in the wrong direction.

**Plan surfacing.** Plan mode produces a real, editable document. The sequence is: the "Agent asks clarifying questions to understand your requirements", then "Researches your codebase to gather relevant context", then writes "a comprehensive implementation plan". Location matters: "Plans are saved by default in your home directory", and "Click 'Save to workspace' to move it to your workspace for future reference, team sharing, and documentation." The user can "review and edit the plan through chat or markdown files", then "Click to build the plan when ready".

**Decisions and alternatives.** The clarifying question step is the alternatives mechanism, and it runs before the plan exists rather than after the code does.

**Take over.** Watch the streaming diff, stop, edit the plan markdown, or edit the code directly. Review is a separate act: "Review" then "Find Issues" runs a dedicated code review where "The agent analyzes proposed edits line by line and flags potential problems", plus an Agent Review in the Source Control tab that compares against the main branch, plus Bugbot on pull requests.

**Why a non coder can follow it.** Partially. The plan being a markdown document you can open, read, and rewrite is the accessible part. The rest assumes diff literacy. Note the sentence the docs use to justify plan mode, which is the founder's problem restated: "the hard part is often figuring out what change should be made".

---

## 5. Replit Agent

The most non expert oriented product in the survey, and the richest source of directly stealable mechanics.

**Stated audience.** "Describe what you want in everyday language. No code or technical knowledge required."

**Plan surfacing.** Plan mode produces "an ordered task list of the development tasks necessary to complete your request" with priorities and dependencies visible. Approval is a two button choice: "Select Start building to approve the plan" or "keep chatting to refine the plan", and on approval "Agent automatically switches to Build mode". The general Agent page frames the same choice as "Accept tasks" or "Revise plan" before Agent modifies anything, and describes plan mode as the place to "Explore different approaches and weigh trade-offs".

Crucially, the plan is not just steps. Per the build-with-agent guide, when the agent finishes thinking a "task plan is ready for review" banner appears with a Review button, and the expanded plan shows **intentions, success criteria, out-of-scope items, and build steps**. Out of scope, stated up front, is the thing almost nobody else does.

**What the user sees while it works.** Two things a non coder can actually parse. First, self testing rendered visually: the agent "navigates through your application like a real user would, clicking around and validating functionality", the user sees "a browser preview within the Agent pane" and can "watch Agent's cursor as it clicks around your app", and afterwards gets an interactive video replay ("click the video to replay the entire testing session", "Use the sliders at the bottom to jump to specific sections of the test") plus a summary, where "Agent reports back with a summary of its tests and automatically fixes any issues that crop up". Second, the preview itself, which the docs teach the user to exercise as an end user would.

**Take over.** Two named affordances. During testing, when the agent hits something only a human can do (a login, for example), it presents "a button to 'Begin take over'", the user does the human part, and the agent resumes. And the safety net: checkpoints. "A checkpoint is a complete snapshot of your Replit App state created automatically by Agent at key development milestones", capturing project files, AI conversation context, environment configuration, agent memory, and optionally database contents. The history view shows "a complete timeline of all checkpoints and their progression" and the control is literally "Rollback to here". Database is excluded by default: "By default, rollbacks do not change your database."

**Why a non coder can follow it.** Four reasons, all copyable. (a) The plan carries success criteria and out of scope, so "did it do the right thing" is answerable without reading code. (b) Verification is shown as a video of the app being used, not as test output. (c) Undo is a timeline with a button, not a git lecture, and it restores the conversation too, so the user is not stranded in a context he no longer recognises. (d) The docs give the user a role: the agent is "quarterback on the field" and the user is "the coach", setting strategy, reviewing outcomes, deciding next moves. The same page lists five habits, of which the operative ones are "Plan the work", "Review and test", and "Use checkpoints instead of trying to untangle a bad change forever".

---

## 6. Lovable

**Layout.** Two panes: the "Chat panel" on the left where "you tell Lovable what to build and follow its progress", and the "Preview" on the right, "a live, interactive version of your app that updates as Lovable works". A project toolbar carries Preview, Files, Code, and More tabs.

**Plan surfacing.** Plan mode produces a structured plan in a dedicated **Plan view**. A plan "typically includes: A high-level overview of the approach, Key decisions, assumptions, and constraints, Components, data models, and APIs, Step-by-step implementation sequencing, [and] Optional diagrams such as schemas, flows, or architecture." The user can "Edit the plan directly as markdown to add constraints, remove steps, or rewrite sections". On approval "the latest approved version is saved to `.lovable/plan.md`" and the product "switches to Build mode". The gate is stated flatly: "Code changes only happen after you approve a plan and Lovable switches to Build mode."

Two items in that list nobody else surfaces: **key decisions, assumptions, and constraints**, and **optional diagrams such as schemas, flows, or architecture**. That is the founder's "graphs and workflows, process flows" requirement, already shipped by a competitor, inside the plan artifact.

**What the user sees while it works.** Build mode shows "visible tasks" covering the "Current step being executed", "Files being modified", "Tools being used (search, web fetch, image generation)", and "Progress through multi-step implementations". The docs state the purpose in the user's own terms: to "follow progress on complex builds, understand the steps being performed, stay oriented during complex changes, and spot issues early if something seems off".

**Take over.** A stop button with an explicit promise: "Lovable keeps all changes made up to that point, so you won't lose completed work." Queued prompts are visible and can be paused, reordered, edited, copied, or removed. An undo button reverts to the previous state. Beyond that: "Lovable saves every change as a version automatically. Preview old versions of your project, revert to an earlier state, and bookmark stable versions." A version opens as a snapshot view, and the more actions menu offers "Open preview in new tab", "View code changes" as a diff, and "Go to message in chat" to recall the reasoning behind a modification. The currently deployed version carries a "Published badge". Important honesty in the docs: "Reverting restores your project's code only ... It does not restore or roll back your database data."

**Direct manipulation.** The preview toolbar gives four modes: "Select elements" ("Point Lovable at one or more elements and request a change in plain language"), "Edit text inline" ("Fix a typo or change wording directly"), "Draw annotation" ("Show a layout or spatial change that's hard to describe"), and "Add a comment" ("Leave feedback for yourself or a teammate"). The instruction to the user is "choose a toolbar mode, point at what you want to change, and describe the update in plain language".

**Why a non coder can follow it.** Pointing at the thing instead of naming the file. Plans that include assumptions and diagrams. A version list where every entry links back to the chat message that caused it. And a Published badge so the user always knows which version is the one the world sees.

---

## 7. Bolt

**Plan surfacing.** Plan Mode is a toggle: the "Plan Mode highlights blue when active. Click it again to turn off and return to Build Mode." It produces discussion, not code, drawing on "Bolt's documentation and other online sources when needed", and it is justified partly on cost, "letting you explore ideas safely, save tokens by avoiding unnecessary code exchanges".

**Decisions and alternatives.** This is Bolt's one genuinely distinctive contribution: responses carry quick action buttons, named in the docs as "Implement this plan", "Show an example", and "Refine this idea". "Implement this plan" auto switches to Build Mode. Alternatives are rendered as buttons at the end of an explanation, so the next move is a click and not a sentence the user has to compose.

**What the user sees while it works.** UNVERIFIED. The support site index lists Getting Started, Best Practices (plan mode, prompting, token efficiency), Cloud, Building, Concepts (version history), Account, and Troubleshooting, but the pages I read do not describe the build time chat, file explorer, editor, terminal, or preview. I am not asserting Bolt's build time visual surface.

---

## 8. v0

**What the docs claim.** The v0 documentation pages I read describe capabilities rather than layout. The one directly relevant sentence: "Real-time preview of your app, with visual progress indicators and rich UI feedback for all agent actions." Also documented: "Automatically fix errors in your code with intelligent diagnostics", and the shipping choice, "Deploy to production immediately, or open a pull request for review."

**UNVERIFIED.** The actual arrangement and naming of v0's chat, preview, code view, version and fork surfaces is not described on the pages I read, and I am not asserting it. The quoted phrase is worth noting only as corroboration that per action visual feedback is now table stakes, not as a description of a specific UI.

---

## 9. Claude Code itself

BrotherMode runs inside this, so these are constraints and building blocks, not merely comparisons.

**Plan mode.** "Plan mode tells Claude to research and propose changes without making them ... edits stay blocked until you approve the plan." Entry is Shift+Tab or prefixing a prompt with `/plan`. The status bar reads `⏸ plan mode on`. When the plan is ready the user gets a three way choice, verbatim: "Yes, and use auto mode", "Yes, manually approve edits", "No, keep planning". And the editing affordance: "Press `Ctrl+G` to open the proposed plan in your default text editor and edit it directly before Claude proceeds." Accepting a plan also names the session from the plan content.

**Decision points as structured questions.** The `AskUserQuestion` tool "Asks multiple-choice questions to gather requirements or clarify ambiguity", answered by "picking an option, or type your own text through the `Other` row or the notes field". Questions stay open until answered unless `askUserQuestionTimeout` is set to `60s`, `5m`, or `10m`, in which case a countdown shows for the last 20 seconds. Note the hard line, which matters for any BrotherMode gate: "The timeout applies only to `AskUserQuestion`'s multiple-choice questions; permission prompts, including plan approval, never auto-resolve on idle."

**Task list.** `TodoWrite` "Manages the session task checklist. Disabled by default as of v2.1.142 in favor of `TaskCreate`, `TaskGet`, `TaskList`, and `TaskUpdate`." The checklist surface exists and has become a task store with its own tools, which is architecturally the same move BrotherMode already made with SQLite.

**The multi session view, the single most transferable artifact in this survey.** `claude agents` opens a full terminal view. A header shows version, model, working directory, and a count of sessions by state. The table is grouped, in this order: **Pinned**, **Ready for review**, **Needs input**, **Working**, **Completed**. Every row carries an icon whose "color and animation show the session's state" (working animated, needs input yellow, idle dimmed, completed green, failed red, stopped grey), a name tinted by the session's `/color`, a one line summary, an age, and an optional `#1234` pull request label at the right edge coloured by status (yellow waiting or failed, green passing, purple merged, grey draft or closed). The docs tell the user to read that label as the outcome: "For a task that ends in a pull request, check this label for the result: review and merge the pull request when its number turns green."

The summary line is generated, not hand written: it is produced "by a Haiku-class model so the row can tell you what the session is doing, what it needs, or what it produced without opening the transcript". Refresh cadence is documented: while working it updates at most every 15 seconds from session output without model requests, a fresh model written summary lands at end of turn, and long turns are rewritten every few minutes to prevent staleness. Pressing Space opens a peek panel with the full sentence, the exact question a waiting session is asking, the result of a finished session, linked pull requests, and a wait time such as "waiting 3m".

**Undo.** Checkpointing "automatically captures the state of your code before each user prompt", keeps snapshots for the 100 most recent checkpoints, survives session resume, and expires with sessions after 30 days. `/rewind` (or double Esc on an empty prompt) lists each prompt sent and offers, verbatim: "Restore code and conversation", "Restore conversation", "Restore code", "Summarize from here", "Summarize up to here", "Never mind". The limits are stated plainly and matter for any promise BrotherMode makes: bash command file changes are not tracked, subagent edits are not restored, external changes are not tracked, and symlinked or hard linked paths are skipped with a `Restored the code, but skipped N files` warning. And the framing: "Think of checkpoints as 'local undo' and Git as 'permanent history'."

**Other visual surfaces available in the terminal.** `/diff` opens "an interactive diff viewer showing uncommitted changes and per-turn diffs" with arrow key navigation between the current git diff and individual Claude turns. `/context [all]` visualises "current context usage as a colored grid" with optimization suggestions and capacity warnings.

**In product onboarding.** The docs say: "run `/powerup` for interactive lessons with animated demos". UNVERIFIED beyond that sentence: secondary sources describe 18 gamified lessons under five minutes each with persistent progress, but I did not open a first party page enumerating them, so treat the count and format as unconfirmed. The confirmed point is that Anthropic ships teaching inside the terminal rather than linking out to documentation, and that it is animated.

---

## 10. Kiro (spec driven development)

Included because it is the closest shipped analogue to BrotherMode's CANVAS.md, and to the idea that the plan is a set of documents.

A spec generates three files: `requirements.md` (or `bugfix.md`) with user stories and acceptance criteria, `design.md` with "technical architecture, sequence diagrams, and implementation approach", and `tasks.md` with "discrete, executable implementation tasks". The workflow is sequential, "Requirements or Bug Analysis, then Design, then Tasks", with approval gates between phases. Requirements use EARS notation, "WHEN [condition/event] THE SYSTEM SHALL [expected behavior]". Task execution shows real time status updates against `tasks.md`, and independent tasks run concurrently in dependency ordered waves: "Wave 1 - all tasks with no dependencies ... Wave 2 - all tasks whose dependencies were satisfied by Wave 1".

UNVERIFIED: the exact button wording of the approval gates. The feature specs page references selecting "Analyze Requirements" from the chat options or the Continue dropdown, but does not spell out each gate's control.

**Why it matters here.** Structured, testable requirements in a fixed sentence template are readable by a non engineer in a way prose is not. WHEN this happens THE SYSTEM SHALL do that is a sentence a founder can approve or reject without knowing a programming language.

---

## 11. Google Jules

Jules generates a plan the user can "review and approve it before any code changes are made", and the environment work (cloning, installing dependencies, modifying files) happens in a VM. Notifications tell the user when "the task completes or needs your input".

The changelog gives dated evidence of the direction of travel:

- **Interactive Plan**, 2025-08-08: "Instead of jumping straight to the solution, Jules will now read your codebase, ask clarifying questions, and work with you to refine the plan."
- **Render Images in Diff Viewer**, 2025-08-22: "Jules now intelligently renders images within the diff viewer, providing an immediate visual context for your modifications."
- **Sample Prompts**, 2025-09-02: clickable sample prompts on the home page that populate the input box.
- **Stacked Diff**, 2025-09-04: "displays diffs for multiple files vertically on a single screen", with a toggle back to the tabbed viewer.
- **Planning Critic**, 2026-01-26: "a secondary agent, the Planning Critic, to review all plans that do not require human intervention", credited with "a 9.5% reduction in task failure rates".

**Why it matters here.** Two things. Sample prompts on the home page are the cheapest onboarding device in this entire survey: the blank input box is the real onboarding failure, and clickable examples fix it. And the Planning Critic is a shipped precedent for BrotherMode's refute style verification being a visible product feature rather than an internal habit.

---

## 12. OpenAI Codex cloud

The delegation model is: the user can "watch the task logs or let the task run in the background", then review "the summary and diff", then "ask Codex to make follow-up changes, or open a pull request when the work is ready". Results are organised into browsable sections including "Chats", "Code reviews", and "Archive", and the docs note the product references "terminal output and file paths" to ground results.

**Why it matters here.** It is the clearest statement of the asynchronous contract: the user is not expected to watch. The deliverable at the end is a summary plus a diff, and the interruption is optional. That is the right default posture for a founder who steps away, and it is the shape BrotherMode's insight ledger should take.

---

# Transferable patterns

Ranked by how directly they answer the founder's complaint. Each names the products that ship it.

**T1. A one line generated status per unit of work, grouped by what the human must do.**
Source: Claude Code agent view (groups Pinned, Ready for review, Needs input, Working, Completed; summary written by a Haiku class model; refreshed at most every 15 seconds while working; peek panel shows the exact question a waiting session is asking). This is the answer to "recurrent insight boxes and key alerts to keep the user engaged". The grouping IS the product: a founder should never scan for what needs him, the view should sort by it. For BrotherMode this is a generated view over store rows and needs no daemon, only regeneration on each event.

**T2. State by colour and shape, never by paragraph.**
Source: Claude Code agent view (icon colour and animation for state, icon shape for process liveness, pull request number coloured yellow, green, purple, grey with the explicit instruction to act when it turns green). Lovable's "Published badge" is the same move. A non engineer reads a colour before he reads a word.

**T3. The plan carries success criteria and out of scope, not just steps.**
Source: Replit ("intentions, success criteria, out-of-scope items, and build steps", surfaced behind a "task plan is ready for review" banner with a Review button). Lovable's plan additionally carries "Key decisions, assumptions, and constraints". Without success criteria, "is it done" is unanswerable to someone who cannot read tests. Without out of scope, every gap looks like a failure.

**T4. Current behaviour versus proposed behaviour, in bullets, before any code.**
Source: Copilot Workspace (current specification and proposed specification as two bulleted lists). The highest value single artifact in this survey for a non expert, and it costs nothing but generation from the store.

**T5. Diagrams inside the plan, not as a separate deliverable.**
Source: Lovable ("Optional diagrams such as schemas, flows, or architecture"), Kiro (`design.md` with sequence diagrams). Mermaid renders natively in Artifacts, so this is nearly free for BrotherMode.

**T6. Decisions offered as a small set of labelled options, with the recommended one identified.**
Source: Claude Code `AskUserQuestion` (multiple choice with an `Other` row and a notes field, and the guarantee that plan approval never auto resolves on idle), Bolt quick actions ("Implement this plan", "Show an example", "Refine this idea"), Replit ("Accept tasks" or "Revise plan"), Cursor (clarifying questions before the plan is written). Alternatives should be clickable, not describable.

**T7. Clarifying questions come before the plan, not after the code.**
Source: Cursor ("Agent asks clarifying questions to understand your requirements", then researches, then plans), Jules Interactive Plan ("Instead of jumping straight to the solution, Jules will now read your codebase, ask clarifying questions").

**T8. A named take over control with an explicit promise about what is kept.**
Source: Replit ("Begin take over" when the agent hits something only a human can do), Lovable stop button ("Lovable keeps all changes made up to that point, so you won't lose completed work"), Devin (stopping the session makes the IDE and terminals writable). The founder's "giving him the hand" needs a button and a sentence about what survives, not an invitation.

**T9. Undo as a timeline of named moments, restoring conversation as well as files, with the limits stated.**
Source: Replit checkpoints ("A checkpoint is a complete snapshot ... created automatically by Agent at key development milestones", restoring files, AI conversation context, config, agent memory, database optional, control labelled "Rollback to here", plus the honest default "By default, rollbacks do not change your database"), Lovable version history (automatic versions, bookmarks, snapshot view, plus the honest caveat "It does not restore or roll back your database data"), Claude Code `/rewind` (six named actions plus a documented list of what it cannot restore). Copy the honesty as much as the mechanism: every one of these products states in its documentation what undo does NOT cover.

**T10. Every change links back to the reason for it, in one click.**
Source: Copilot coding agent ("Each commit message includes a link to the session logs, so you can trace why a change was made during code review or an audit"), Lovable ("Go to message in chat" from a version), Devin Progress tab (click a step to open its detail in context). For BrotherMode the store already holds the causal chain, so this is a join, not a new feature.

**T11. Verification shown as evidence a non coder can judge.**
Source: Replit app testing (browser preview inside the agent pane, watch the cursor click, video replay with section sliders, then "Agent reports back with a summary of its tests"), Cursor Review then Find Issues, Jules Planning Critic. BrotherMode cannot produce a video, but it can produce a plain English "what I checked and what it proved" block per claim, and that is the same contract.

**T12. Teaching delivered in the tool, at the moment of use, with examples pre loaded.**
Source: Claude Code `/powerup` ("interactive lessons with animated demos"), Jules sample prompts on the home page that populate the input box. The blank prompt box is the real onboarding wall.

**T13. Progress named in plain nouns: the step, the file, the tool.**
Source: Lovable visible tasks ("Current step being executed", "Files being modified", "Tools being used (search, web fetch, image generation)"), stated in the docs as being so the user can "stay oriented during complex changes, and spot issues early if something seems off".

**T14. Anchor views to artifacts that already exist rather than inventing a parallel universe.**
Source: the Copilot arc. Copilot Workspace built a bespoke four stage surface and the standalone product did not persist (manual repo archived, verified). The successor hangs everything on issues, pull requests, commits, and logs. For BrotherMode the pre existing artifacts are the store rows, CANVAS.md, and the git repo, and every view should be a projection of those.

**T15. A stated role metaphor so the founder knows what his job is.**
Source: Replit ("quarterback on the field" versus "the coach", plus five named habits: be specific, plan the work, add context, review and test, use checkpoints). This is cheap, it is copy, and it converts a passive watcher into a participant.

---

# Patterns that would be WRONG for BrotherMode

Each names the constraint it violates.

**W1. Live streaming panes (shell, IDE, browser, cursor video).**
Ships in: Devin (Shell, IDE, Interactive Browser), Replit (live cursor and video replay), Cursor (streaming diff).
Wrong because: BrotherMode is standard library Python with no daemon and no server, and an Artifact has no network access at render time, so nothing can stream into it. Worse, it inverts the founder's own constraint: a shell pane is a log, and the founder cannot read logs and should never have to. Devin's Shell tab is the exact surface this product must not build.

**W2. An embedded editor as the handback mechanism.**
Ships in: Devin (stop the session and the VS Code pane becomes writable), Replit (the workspace is the IDE).
Wrong because: BrotherMode has no hosted editor and no environment of its own. Handback here has to mean a document plus a repository state plus a named next command, not a text area. Take the affordance (T8) and the promise sentence, reject the mechanism.

**W3. Auto refreshing dashboards and polling views.**
Ships in: every hosted product above, implicitly.
Wrong because: an Artifact is a self contained page with inline CSS and JS and no external requests. Any BrotherMode view is a SNAPSHOT generated at a moment in time. The design must therefore make the snapshot's timestamp and its generating event prominent, and regeneration must be an explicit act, not an animation pretending to be live. A view that looks live but is stale is worse than a view that is honestly dated.

**W4. A user editable plan file that both human and agent write.**
Ships in: Cursor (plan saved to the home directory, "Save to workspace", edited "through chat or markdown files"), Lovable (`.lovable/plan.md`), Kiro (`requirements.md`, `design.md`, `tasks.md`).
Wrong because: BrotherMode's store is the single source of truth and any view is GENERATED from rows and never hand maintained. A writable plan file creates a second truth that drifts. Adopt the SHAPE (a readable plan document with criteria, scope, and diagrams) and reject the MECHANIC: the document must be a read only projection, and edits must go back through the store, for example by the founder answering a structured question that writes a row which then regenerates the document.

**W5. Approval gates on every phase.**
Ships in: Kiro (requirements gate, then design gate, then tasks gate).
Wrong because: two compounding problems. First, gate fatigue on a founder who wants to watch progress, not sign three forms per feature. Second, BrotherMode has a hard rule that nothing may write before setup consent, so consent is already a distinct, high stakes event, and burying it in a queue of routine phase approvals trains the founder to click through it. Use one meaningful gate per decision, plus non blocking alerts, and keep the setup consent visually distinct from every other prompt. Inherit Claude Code's own safety line: "permission prompts, including plan approval, never auto-resolve on idle".

**W6. Token, credit, and cost meters as the headline progress signal.**
Ships in: Copilot coding agent (session log shows "token usage, and session length"), Bolt (Plan Mode partly justified as "save tokens by avoiding unnecessary code exchanges"), Claude Code `/context` grid.
Wrong because: it measures the machine, not the work, and for a non engineer founder a burning meter reads as a threat rather than as information. Cost belongs in a secondary panel, never in the insight box or the alert. The headline unit must be the deliverable and its state.

**W7. Screenshots or video of the running application as proof of work.**
Ships in: Replit app testing.
Wrong because: BrotherMode does not run the user's application, has no browser, and no dependencies to acquire one. Promising visual proof it cannot produce would be the single most damaging over claim in this design. The substitute is a written evidence block per claim: what was checked, the exact command, and what the output proved, rendered as a card rather than as a log.

**W8. Vibe framing that hides the mechanism.**
Ships in: Replit's "No code or technical knowledge required" positioning and its vibe coding material.
Wrong because: the founder's requirement explicitly ends with "fully understanding what is happening and giving him the hand to take over and continue development him or herself". Hiding the mechanism directly defeats the handback goal. BrotherMode should be plain, not magical: name the file, name the command, name the reason, in words a non engineer can read. Take Replit's role metaphor (T15) and its plain language, reject its concealment.

**W9. Rich interactive chat widgets as the primary channel.**
Ships in: every hosted web product above.
Wrong because: BrotherMode runs inside Claude Code, which is a terminal and a chat. Inline widgets and Artifacts are available in some surfaces and not in a bare terminal. The durable surface must therefore be a generated FILE (readable in any editor, diffable, committable), with the Artifact as the rich rendering of that same file, and terse terminal text as the always available fallback. Anything that exists only as a chat widget is lost the moment the session ends, which is exactly the failure the founder is complaining about with chat prose today.

**W10. A bespoke parallel UI universe.**
Ships in: Copilot Workspace, as the cautionary example.
Wrong because: it is the most expensive thing to build and the first thing to rot. See T14. Every BrotherMode view should be a projection of the store, CANVAS.md, or the repo, and should degrade gracefully to those artifacts if the view generator is ever removed.

---

# What I did not verify

Stated plainly.

1. The Copilot Workspace technical preview sunset date. Verified only that the user manual repo is archived (`gh api`, `"archived": true`, `pushed_at` 2025-09-02) and that a distinct Copilot coding agent is current on docs.github.com.
2. Bolt's build time interface (chat, file tree, editor, terminal, preview). Only Plan Mode is sourced. The rest of Bolt's surface is unread.
3. v0's interface layout, version and fork surfaces. Only the capability sentence about "visual progress indicators and rich UI feedback for all agent actions" is sourced.
4. Whether Devin exposes a pre execution editable plan artifact or a confidence signal. I read four Devin pages, found the Progress tab, found no plan artifact and no confidence surface.
5. Kiro's exact approval gate controls between phases. The phases and the three files are sourced, the button wording is not.
6. The `/powerup` lesson count, format, and persistence. Only the first party sentence "run `/powerup` for interactive lessons with animated demos" is sourced. Secondary sources claim 18 gamified lessons under five minutes with persistent progress, which I am not asserting.
7. Windsurf Cascade, Amp, Factory, and Aider were not researched at all. Time went to the twelve products above.
8. No product was verified by using it. Every claim comes from documentation, which describes intent and can lag the shipped build.
