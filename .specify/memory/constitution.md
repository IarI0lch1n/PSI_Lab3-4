<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles: existing governance principles retained; no principle renames
- Added sections: CurrencyHub Architecture and Technology Constraints
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

## CurrencyHub Architecture and Technology Constraints

### Technology Stack
The project MUST be implemented as one full-stack currency conversion and analytics system with the following technology boundaries:

- The backend MUST use Python 3, FastAPI, SQLAlchemy 2, Microsoft SQL Server, Alembic migrations, and pytest.
- The web client MUST use Angular and TypeScript and MUST be a responsive web application.
- The mobile client MUST use Flutter and Dart, with Android as the primary target platform.
- The mobile client MUST run in Android Studio Emulator for development and verification.
- Both clients MUST use the same Python REST API.
- Neither frontend MAY connect directly to SQL Server.
- Neither frontend MAY directly depend on third-party API credentials.

### Architecture
The backend MUST follow Clean Architecture with the following conceptual layers:

- Domain
- Application
- Infrastructure
- API

Business logic MUST NOT directly depend on FastAPI, SQLAlchemy, Microsoft SQL Server, BNM, CoinGecko, or other infrastructure frameworks.

Object-Oriented Programming MUST be used where appropriate. All SOLID principles MUST be respected:

- Single Responsibility Principle
- Open/Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

Dependency Injection MUST be used. Database access MUST use repository abstractions. External rate providers MUST be accessed through abstractions.

### Design Patterns
Patterns MUST solve actual architectural problems and MUST NOT be included only for demonstration. The architecture SHOULD use:

- Adapter for BNM and cryptocurrency provider integrations
- Strategy for rate resolution and fallback behavior
- Factory Method for constructing or selecting exchange-rate providers
- Facade for exposing currency, conversion, and analytics use cases to the API
- Repository pattern for persistence
- Unit of Work where transactional consistency requires it

### Data Sources and Currency Coverage
Fiat exchange rates MUST be sourced from the National Bank of Moldova (BNM). Cryptocurrency rates MUST be sourced from CoinGecko or another explicitly documented cryptocurrency API.

Supported currencies MUST include at minimum:

Fiat:
- MDL
- USD
- EUR
- RUB
- CNY
- GBP
- RON
- UAH
- CHF
- JPY

Crypto:
- BTC
- ETH
- SOL
- BNB
- XRP
- ADA
- DOGE
- USDT

### Financial Correctness
All monetary calculations MUST use decimal arithmetic. Binary floating-point MUST NOT be used for financial calculations.

All exchange rates MUST be normalized through a consistent internal representation. The conversion engine MUST support:

- fiat → fiat
- fiat → crypto
- crypto → fiat
- crypto → crypto
- same currency → same currency

Same-currency conversion MUST return the original amount.

Invalid monetary input includes:

- empty input
- zero
- negative values
- non-numeric input

Such values MUST NOT be converted.

### Functional Requirements
The system MUST provide the following capabilities:

1. Classic currency converter with amount, source currency, target currency, result, rate date, and data source.
2. Multi-currency converter where the user enters a value into one currency field and all other visible currencies are recalculated using the same rate snapshot.
3. Current rates screen.
4. Seven-day analytics.
5. Thirty-day analytics.

Analytics MUST contain:

- time-series values
- minimum
- maximum
- average
- absolute change
- percentage change
- trend: growth, decline, or unchanged

### Persistence
Current and historical rate data MUST be persisted in Microsoft SQL Server. The database MUST retain enough data to build both 7-day and 30-day analytics. Schema evolution MUST be managed through Alembic migrations.

### Resilience and Offline Support
External provider failures MUST NOT crash the backend. The last successfully obtained rate data MUST be persisted and available as fallback data.

When BNM has no rate for a weekend or holiday, the system MUST use the latest valid previous rate and clearly identify it as fallback data. Flutter MUST maintain a local cache of the last successful snapshot. The Angular web application MUST maintain an appropriate local cache of the last successful snapshot.

When cached data is displayed, the client MUST clearly show that the data is cached or stale and MUST display the timestamp or date of the cached data.

### Security
Secrets MUST NOT be committed to Git. Database credentials and external API credentials MUST be provided through environment configuration.

SQL Server credentials MUST NOT exist in frontend code. Third-party API secrets MUST remain on the backend.

### Testability
Tests MUST NOT require live BNM or CoinGecko services. External providers MUST be replaceable by mocks, stubs, or fake implementations.

Backend unit tests MUST cover at minimum:

- BNM response parsing
- cryptocurrency provider response parsing
- direct conversion
- reverse conversion
- fiat/crypto conversion
- same-currency conversion
- invalid input
- empty or malformed provider response
- cached or fallback behavior
- 7-day statistics
- 30-day statistics
- empty historical datasets

Important frontend validation and presentation logic MUST also be testable.

### Git Workflow
Specifications MUST be committed before implementation. The project MUST use meaningful development branches, including separate stages for:

- specifications
- backend
- database
- web frontend
- mobile frontend
- analytics
- offline/cache
- tests

Changes MUST be integrated into main through Pull Requests. Commit history MUST demonstrate the development process.

## Governance

This Constitution governs project decision-making and supersedes informal practices that conflict with it. Amendments MUST be proposed in writing, reviewed for impact, and approved before taking effect. Any material change MUST include a clear rationale, any migration or compatibility implications, and a version update.

The versioning policy is semantic versioning: MAJOR changes remove or redefine core governance requirements, MINOR changes add or materially expand principles or sections, and PATCH changes clarify or refine existing guidance without changing intent. The project MUST record the ratification date and the amendment date in the constitution header.

Compliance review occurs at the same points as normal project review: pull requests, milestones, and release readiness checks. Reviewers MUST confirm that changes remain aligned with this Constitution and that unresolved exceptions are explicitly documented.

**Version**: 1.1.0 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
