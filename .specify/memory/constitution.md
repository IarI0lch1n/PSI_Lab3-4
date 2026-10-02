<!--
Sync Impact Report
- Version change: 0.0.0 -> 1.0.0
- Modified principles: initial placeholder scaffold -> I. Clarity and Intent, II. Evidence-Driven Change, III. Quality Before Delivery, IV. Collaboration and Review, V. Change Safety and Maintainability
- Added sections: Additional Constraints; Development Workflow
- Removed sections: none
- Follow-up TODOs: none
-->

# PSI Lab 3-4 Constitution

## Core Principles

### I. Clarity and Intent
All work MUST begin with a clear problem statement, a defined outcome, and explicit acceptance criteria. Scope, constraints, and assumptions MUST be stated before implementation begins so that decisions remain traceable to user need and project intent.

### II. Evidence-Driven Change
Every significant decision MUST be grounded in observable evidence such as requirements, test results, logs, metrics, or direct verification. Changes without proof of impact are not considered valid until they are validated in context.

### III. Quality Before Delivery
Features, fixes, and configuration changes MUST satisfy agreed acceptance criteria and preserve the reliability of the existing system. No work is complete until the relevant verification has been performed and the result is recorded.

### IV. Collaboration and Review
Work MUST be reviewed by at least one other contributor before it is merged or handed off. Review feedback that identifies correctness, safety, maintainability, or scope concerns MUST be addressed before completion.

### V. Change Safety and Maintainability
Changes MUST be small, readable, and explainable. Complexity MUST be justified and documented, and any added dependency, risk, or migration requirement MUST be addressed before release.

## Additional Constraints

This project MUST maintain a clear separation between governance artifacts and application work. Constitutional updates MUST be recorded in .specify/memory/constitution.md, while feature implementation, testing, and deployment work remain governed by their respective task and review processes.

Sensitive information MUST not be committed to the repository. Secrets, credentials, tokens, and personal data MUST be stored outside the project and referenced only through secure configuration channels.

## Development Workflow

All work MUST follow a defined lifecycle: identify the requirement, validate the assumptions, implement the smallest viable change, verify the result with the relevant evidence, and review the outcome before completion. Documentation and operational notes MUST be kept current when they affect how the project is used or maintained.

## Governance

This Constitution governs project decision-making and supersedes informal practices that conflict with it. Amendments MUST be proposed in writing, reviewed for impact, and approved before taking effect. Any material change MUST include a clear rationale, any migration or compatibility implications, and a version update.

The versioning policy is semantic versioning: MAJOR changes remove or redefine core governance requirements, MINOR changes add or materially expand principles or sections, and PATCH changes clarify or refine existing guidance without changing intent. The project MUST record the ratification date and the amendment date in the constitution header.

Compliance review occurs at the same points as normal project review: pull requests, milestones, and release readiness checks. Reviewers MUST confirm that changes remain aligned with this Constitution and that unresolved exceptions are explicitly documented.

**Version**: 1.0.0 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
