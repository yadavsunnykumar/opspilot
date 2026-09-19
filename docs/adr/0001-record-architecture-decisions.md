# 1. Record architecture decisions

Date: 2026-09-17

## Status
Accepted

## Context
OpsPilot makes several significant technical choices (queue library, vector store,
streaming protocol). We need a lightweight way to record why each choice was made.

## Decision
We record every significant decision as an ADR in `docs/adr/NNNN-title.md`
with Context, Decision, Alternatives and Consequences.

## Consequences
New contributors and interviewers can understand the reasoning behind the design.
Each ADR is added in the same pull request as the change it describes.
