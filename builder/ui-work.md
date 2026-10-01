# UI work for the Pyrycode Mobile builder

Read this when the ticket is UI-visible or carries a `## Figma` section. The plan is where design intent gets pinned, because there is no separate design stage, and the verifier judges visual fidelity against the Figma node your plan names.

## Read the Figma node before planning

The canonical Figma file is `g2HIq2UyPhslEoHRokQmHG`. Take the node id from the ticket's URL, such as `15-8` for the channel list.

1. Fetch the design context for the node, which gives layout, typography, colour tokens and spacing. On Claude that is `mcp__plugin_figma_figma__get_design_context(fileKey: "g2HIq2UyPhslEoHRokQmHG", nodeId: "<nodeId>")`. Load the Figma design-to-code skill first when your runtime has one. Under Codex the tool names differ, so discover the Figma read tools available to you.
2. Fetch a screenshot of the node with `get_screenshot` and look at it. Write the visual summary from what you see, checked against the structured data, not from the data alone. You compare your result against this screenshot before opening the PR.
3. If the design context comes back truncated, as it does for complex frames such as a channel list with seeded rows, fetch `get_metadata` for the node map, then `get_design_context` on the children you need.
4. For design-token work, such as a new colour token, theme slot or variable, read the values with `get_variable_defs` on a node that uses the variable, using `search_design_system` to find one by name. Write the hex values into the plan. They then survive a continuation leg or a rework, which a later Figma call might not; mobile #119 spent four rework cycles on tickets that deferred to Figma access that later drifted.

Read Figma only through these tools. A web search cannot see a signed-in design, and a browser attempt on the Figma site was refused by Codex approval review on #1210. If the Figma tools are unavailable or fail to authenticate, stop as for a missing tool, unless the ticket itself supplies the design values and says not to wait on Figma access. Planning UI from the ticket text alone is how Phase 1's 28 tickets drifted into generic Material screens.

## Design source section

The plan carries this section on every UI-visible ticket. The verifier's fidelity check keys on its heading.

```markdown
## Design source

**Figma:** https://www.figma.com/design/g2HIq2UyPhslEoHRokQmHG?node-id=<nodeId>

One to three sentences: the layout shape, the Material 3 components used, the key tokens, such as which `Schemes/*` colours and which text styles, and any decorations such as gradients, icons or overlays that must be reproduced.
```

When the ticket's Figma section says `N/A` with a reason, write the same `N/A` and reason here.

## Translate the design into Compose

The design context output is usually React and Tailwind. Treat it as reference data, not code.

- **Colours** come from `MaterialTheme.colorScheme`. If Figma uses `Schemes/Primary`, use `MaterialTheme.colorScheme.primary`. Material 3 derives the tonal palette from seed colours, so a seed value will not appear verbatim in `Color.kt`; use the role tokens.
- **Typography** comes from `MaterialTheme.typography`. The kit's `M3/<category>/<size>` style names map directly, such as `titleMedium` or `labelSmall`.
- **Spacing and sizes** are `dp` values in `Modifier.padding` and `Modifier.size`, taken from Figma's auto-layout padding and gaps.
- **Components** are Material 3 where one exists, such as `Button`, `IconButton`, `Card`, `TopAppBar`, `LazyColumn`, `ModalBottomSheet` or `AlertDialog`. Build a custom one only when Material 3 has no equivalent.
- **Assets** come from the design. When the design context returns local SVG or PNG sources for icons or logos, download them under `app/src/main/res/drawable/`. Do not substitute a package icon or a placeholder when a source is available, and add no new icon packages.

Give every screen-level composable a `@Preview`, in light and dark where the palette differs.

## Validate before the PR

Compare what you built with the Figma screenshot: layout, typography, colours through tokens, interactive states, assets and decorations. A preview is your interpretation, so the screenshot stays the reference. When the ticket asks for screenshot comparisons, capture the real screen as the product repo's `docs/knowledge/features/development-verification.md` describes under "Compose evidence" and "Emulator and real evidence", and record the capture paths in the PR.

If a difference cannot be reconciled, such as a `Schemes` variable missing from `Theme.kt` or a shape Material 3 does not provide, document it in a code comment and in the PR body. The verifier fails a silent divergence.

## Check existing coverage on visual changes

A visual change can break layout or interaction tests you did not touch. Search both `app/src/sharedTest` and `app/src/androidTest` for the affected screen and its shared header, footer, fields, system insets and keyboard behaviour, and run the relevant existing methods along with your new tests. Use the focused device command in `device-tests.md` for affected device-only coverage, even when you did not edit that file.

When a design intentionally changes geometry, reconcile the old assertions with the current acceptance criteria and cite the reference in the PR. Do not delete or loosen a failing assertion just to get green. Measure visible bounds separately from invisible touch areas. When controls or fields move or resize, prove focus and action routing with real pointer taps at the field surface and at neighbouring control edges; a screenshot or a semantic click cannot prove a hit area. Record which existing tests ran and any justified expectation change in the PR. The dispatcher still owns the full suite.
