# CurrencyHub Agent Instructions

Repository root:
D:\PSI_Lab3-4

## Source of truth

Before implementation work, read:

- specs/001-currencyhub-platform/spec.md
- specs/001-currencyhub-platform/plan.md
- specs/001-currencyhub-platform/tasks.md
- specs/001-currencyhub-platform/research.md
- specs/001-currencyhub-platform/data-model.md
- specs/001-currencyhub-platform/contracts/rates-api.md
- specs/001-currencyhub-platform/quickstart.md

The task list in:
specs/001-currencyhub-platform/tasks.md

is the source of truth for implementation progress.

## Current state

Current feature branch:
us2-conversion

Completed tasks:
T001-T033

Next:
T034

Then:
T035

Do not redo completed tasks.

## Working method

For each task:

1. Inspect existing implementation and relevant specs first.
2. Implement only the current task.
3. Add required tests.
4. Run focused tests.
5. Run the relevant complete test suite.
6. Run analyzer/build/formatter checks.
7. Run `git diff --check`.
8. Inspect the diff for scope mistakes.
9. Fix all failures before considering the task complete.
10. Mark only the completed task `[x]` in tasks.md.
11. Commit with a meaningful commit message.
12. Push the current branch.
13. Continue automatically to the next task.

Do not stop after reporting a test failure.
Diagnose and fix it, then rerun verification.

## Git authorization

You are authorized to run:

- git status
- git diff
- git add
- git commit
- git push
- git fetch
- git pull
- git checkout
- git switch
- git branch
- gh pr create
- gh pr view
- gh pr checks
- gh pr merge

Do not force-push.
Do not rewrite existing history.
Do not delete unrelated branches.
Do not modify main directly except by merging a completed feature PR.

Prefer one commit per task.

## User-story completion

When the last task of a user story is finished:

1. Run all relevant backend/web/mobile tests.
2. Run static analysis and builds.
3. Run formatting checks.
4. Run `git diff --check`.
5. Ensure working tree is clean.
6. Push the feature branch.
7. Create a GitHub PR to main.
8. Verify the PR is mergeable and checks are green.
9. Merge using a normal merge commit, not squash.
10. Delete the feature branch.
11. Checkout main.
12. Pull latest main.
13. Create the next feature branch based on the next task group.
14. Continue from the next unchecked task.

## Backend

Path:
backend

Python:
backend\.venv\Scripts\python.exe

Full tests:

.\.venv\Scripts\python.exe -m pytest -q

Automated tests must not make live requests to BNM or CoinGecko.

Use fake/mock providers.

Financial calculations must use Decimal.
Never use float for money or rates.

## Angular

Path:
web

Validation:

npm test -- --watch=false
npm run build

Use Prettier on changed files.

Do not perform financial conversion using Number, parseFloat, or binary
floating-point arithmetic.

The backend is authoritative for financial calculations.

## Flutter

Path:
mobile

Validation:

flutter analyze
flutter test
dart format --output=none --set-exit-if-changed lib test

Financial values returned by the API must remain strings.

Do not use double or num for financial conversion calculations.

If Flutter modifies analysis_options.yaml incidentally, restore it before
committing.

## Architecture

Backend:
- Python 3.12
- FastAPI
- SQL Server
- SQLAlchemy 2
- Alembic
- pytest

Web:
- Angular
- TypeScript

Mobile:
- Flutter
- Dart

Follow the existing Clean Architecture boundaries and existing project style.

## Conversion formula

All rates are normalized to MDL.

converted_amount =
    amount * source_rate_to_mdl / target_rate_to_mdl

Backend calculation uses Decimal only.

Same-currency conversion returns the original amount and rate value 1, but its
applicable rate entry must still exist.

## Freshness policy

Primary state:

- live
- fallback
- cached

Separate independent flags:

- is_fallback
- is_stale

Never infer is_fallback or is_stale purely from freshness_state.

## Provenance

A conversion has separate source and target provenance.

Never collapse mixed-provider conversions into one shared:

- provider
- effective time
- freshness state
- fallback flag
- stale flag

## Reporting

After each task, report briefly:

- task completed
- files changed
- focused checks
- full checks
- commit SHA
- push result

Then continue automatically unless blocked by:
- a genuine unresolved requirement ambiguity
- credentials/authentication
- an operation outside the repository that requires approval
- a potentially destructive operation