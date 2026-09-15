# Story Agent Tool-Call Limit Increase

## Goal

Allow the Story Agent to use up to 12 tool calls during one generation run,
while retaining the existing protection against unbounded tool-calling loops.

## Scope

- Change the `StoryAgent` default limit from 6 to 12.
- Update the limit-exceeded error message to describe the 12-call limit.
- Update unit tests so 12 calls succeed and the 13th call fails.

No prompt, database, API, or workflow behavior changes are included.

## Validation

Run the Story Agent unit tests and confirm the updated boundary behavior.
