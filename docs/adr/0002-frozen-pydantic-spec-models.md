# 2. Spec models are frozen Pydantic models validated at construction

## Status

Accepted

## Context

A diagram is described by the user and drawn later. Mistakes such as a misspelt option,
an edge pointing at a missing box or an invalid colour should surface when the spec is
built, not as a confusing failure inside matplotlib. Specs also need to load from dicts
and JSON, and to be reused and varied safely.

## Decision

Every spec model extends a `Spec` base that is frozen and forbids extra fields. Variants
are made with `model_copy(update=...)`.

Components that can sit in a tree carry a `kind` literal, and the unions use a
discriminator on `kind`, so nested specs load from dicts and JSON. Data loaded from a
dict must include `kind`; objects built in Python get it by default.

Checks that span components (duplicate box IDs, unknown theme roles, edges that refer to
missing boxes, self-loops) run in one validator on `Diagram` and report every problem in
a single error, with the offending IDs and the valid choices. The error hides the raw
input so a large spec is not dumped into the message.

Colours are validated with matplotlib's colour parser, so any colour matplotlib accepts
is accepted here, and the original spelling is kept.

## Consequences

Mistakes are caught early with readable messages. Specs can be compared with `==`,
serialised and reloaded without loss. The cost is a `kind` marker
in dict input, and a hard dependency on matplotlib for colour parsing in the spec
modules. Nested `dict` values such as `Theme.roles` are not deep-frozen; they are
treated as immutable by convention.
