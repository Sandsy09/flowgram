# 1. Record architecture decisions

## Status

Accepted

## Context

We need to record the architectural decisions made on this project so future
contributors (including ourselves) understand why the codebase looks the way
it does, not just what it currently looks like.

## Decision

We will use Architecture Decision Records, as described by Michael Nygard in
[Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

Each ADR is a numbered Markdown file in `docs/adr/`. Records are immutable:
once accepted, a decision is changed by writing a new ADR that supersedes it,
not by editing this one.

## Consequences

Anyone wanting to understand a past design decision can read the ADR instead
of reverse-engineering it from code or asking around. Decisions that turn out
to be wrong are recorded as history, not silently erased.
