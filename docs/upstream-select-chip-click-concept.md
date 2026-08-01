# Upstream feature-request concept: an "activate" interaction for `select` chips

## Status: concept only, not a diff — not yet opened anywhere (by design, see below)

## Why this exists

`wifi_geolocation`'s Configure flow (this project) currently needs two
separate UI elements to manage credentialed, reorderable backends:

1. A draggable chip list (`SelectSelector(multiple=True, reorder=True)`,
   via the local patch in `_selector_patch.py` — see
   `docs/upstream-reorder-selector-pr/` for that gap) for enabling/
   ordering backends.
2. A second, separate "Re-enter credentials for" multi-select
   (`custom_components/wifi_geolocation/config_flow.py`,
   `_reenter_credentials_field`) listing the same backends again, so a
   user can force one back into the credential-prompt queue (e.g. after
   rotating a revoked API key) without a disable/re-enable round-trip.

The idea: fold these into one interaction. In the same chip list already
used for ordering, *clicking* a chip (as opposed to *dragging* it) could
open that backend's credential step directly — no second field needed.

## Why this is a feature request, not a ready diff

The earlier `reorder` contribution (see `docs/upstream-reorder-selector-pr/`)
was a precise, mechanical, already-precedented gap: the frontend
(`ha-selector-select.ts`) already fully implemented drag-to-reorder, and
only a Python-side schema key was missing. This is different in kind, not
just degree:

- **Frontend**: `ha-selector-select.ts`'s chip rendering would need to
  distinguish a plain click (pointerdown + pointerup with no meaningful
  movement) from the start of a `ha-sortable`/SortableJS drag — a real
  but bounded UI change.
- **Protocol**: there is currently no concept, anywhere in HA's
  `data_entry_flow` config-flow system, of a single form *field*
  triggering a distinct server round-trip mid-form. Flows are strictly
  "fill out every field on this step → submit → server processes the
  whole step and decides the next one." Making a chip click do something
  server-visible before the rest of the form is submitted is a new
  interaction pattern for config flows generally, not a selector-only
  change — the actual design surface here is bigger than the selector
  file itself.

That protocol question needs input from HA's frontend/config-flow
maintainers, not just a mechanical patch — hence "concept," not a diff
with test coverage the way the `reorder` PR was.

## Sketch of a minimal version, for discussion

Reuse existing form-submission plumbing rather than inventing a new
websocket command, mirroring the `reorder` PR's philosophy of extending
what already exists over building something new:

- New `SelectSelectorConfig` flag, e.g. `activatable: bool` (only valid
  alongside `multiple: True`, same guard pattern as `reorder`).
- Clicking a chip (not dragging it) immediately submits the current form
  values, with the clicked option's value also present under a reserved
  key (e.g. `_activated_option`) alongside the field's normal value.
- The step handler checks for that key first; if present, it can
  short-circuit to a different next step (e.g. this project's
  `backend_config` step for that specific backend) instead of treating
  it as a normal submit.

This is a sketch, not a spec — the reserved-key approach in particular
is the kind of thing that needs a maintainer's opinion before it's worth
writing a real patch.

## What this project would do with it

If this shipped, `wifi_geolocation`'s Configure flow would drop
`_reenter_credentials_field`/`CONF_REENTER_CREDENTIALS` entirely (see
`custom_components/wifi_geolocation/config_flow.py`) and let clicking a
backend's chip open its `backend_config` step directly — one UI element
instead of two, matching the user's original ask that prompted this
concept.

## Next step

Not opened on `home-assistant/frontend` or `home-assistant/architecture`
yet. This is a bigger ask than the `reorder` PR (protocol design, not a
mechanical gap), so it's worth confirming you still want it filed as-is
— likely best framed as a discussion/feature-request issue on
`home-assistant/architecture` (protocol-level proposals go there, not
directly as a frontend PR) rather than something with an attached patch.
