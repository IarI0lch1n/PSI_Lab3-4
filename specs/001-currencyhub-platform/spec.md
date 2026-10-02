# Feature Specification: CurrencyHub

**Feature Branch**: `001-currencyhub-platform`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "CurrencyHub is a currency conversion and exchange-rate analytics application available through both a web application and a mobile application. The product must provide users with current fiat and cryptocurrency exchange rates, currency conversion, multi-currency comparison, historical analytics, and useful offline behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open the app and view current market data (Priority: P1)
A user opens CurrencyHub and must immediately see current currency information without creating an account or signing in. For every currency shown, the user needs to identify its provider, effective date/time, and freshness state; these may differ between currencies even when they are part of the same validated snapshot. This is the primary product entry point and must work consistently on web and mobile.

**Why this priority**: The product is informational and must provide immediate value on first use without onboarding friction.

**Independent Test**: A user can open the app and view supported currencies without signing in, identify each currency's rate provider, effective date/time, live/fallback/cached status, and distinguish the snapshot collection/validation time from the individual rate times.

**Acceptance Scenarios**:

1. **Given** the user opens the application, **When** the app loads, **Then** the user sees current exchange-rate information for supported currencies without creating an account.
2. **Given** the user views the current rates screen, **When** they examine a currency row, **Then** they can identify the currency code, name, value, provider, effective date/time, freshness state, and whether fallback was used for that currency.
3. **Given** a validated snapshot contains currencies from different providers or with different effective times, **When** the user views current rates, **Then** each currency retains its own context and the snapshot collection/validation time is not presented as every rate's effective time.

---

### User Story 2 - Convert one amount between supported currencies (Priority: P1)
A user needs to convert a value from one supported currency to another and must be able to trust the result and understand the rate context for both currencies used. The two rates may come from different providers and have different effective times or freshness states, especially for fiat-to-cryptocurrency conversions. The conversion must reject invalid values and remain usable for same-currency conversions.

**Why this priority**: Classic conversion is the core task and the main reason users install and use the product.

**Independent Test**: A user can enter a valid amount and complete a conversion while identifying the source and target rate contexts separately, including provider, effective time, freshness, and fallback status; invalid and unavailable-rate cases receive clear feedback.

**Acceptance Scenarios**:

1. **Given** a user enters a valid amount and selects source and target currencies, **When** they submit the conversion, **Then** the app displays the converted result and the context for both rate entries: currency, provider, effective date/time, live/fallback/cached state, and whether fallback was used. The source-rate context corresponds to the selected source currency and the target-rate context to the selected target currency. The result includes a reference identifying the validated snapshot used. The pair rate is expressed as target-currency units per one source-currency unit and corresponds to the displayed result. The result is not attributed to one provider when the two rates have different providers.
2. **Given** the user enters a blank, zero, negative, or non-numeric amount, **When** they try to convert, **Then** the app blocks the action and shows a clear validation message.
3. **Given** the user selects the same source and target currency, **When** conversion is performed, **Then** the result equals the original amount and the displayed provenance identifies the one applicable rate without implying separate unrelated sources.
4. **Given** one rate is live while the other is fallback or cached, **When** the user converts, **Then** the app identifies each leg's state independently and does not present the pair as uniformly live.
5. **Given** no permitted live, fallback, or cached rate is available for either required currency, **When** the user requests a conversion, **Then** no converted result is presented and the app identifies which currency rate is unavailable.

---

### User Story 3 - Compare many currencies from one rate snapshot (Priority: P1)
A user wants to enter one value and see all visible currencies updated together from the same validated snapshot so they can compare values quickly without mixing snapshots. Each visible currency must retain its own provider, effective time, freshness state, and fallback status, even when those differ across currencies.

**Why this priority**: Multi-currency comparison drives practical decision-making by comparing many currencies at once.

**Independent Test**: A user can enter an amount in one currency field and see all visible currencies recalculated from the same snapshot while identifying the provenance and freshness of each currency value.

**Acceptance Scenarios**:

1. **Given** the user is on the All Currencies screen, **When** they enter an amount in one displayed currency field, **Then** all other visible values recalculate from the same snapshot and each value's provider, effective date/time, freshness state, and fallback status remain identifiable.
2. **Given** the user changes the entry currency, **When** they type a new amount, **Then** the new source currency becomes active and all other values update from the same snapshot.
3. **Given** a refresh occurs, **When** new rate data has not been validated yet, **Then** the previously usable snapshot remains in place and values from different snapshots are not mixed. Different effective times within that one snapshot are allowed and remain visible per currency.
4. **Given** the snapshot includes currencies from multiple providers or with different freshness states, **When** the user compares values, **Then** the context is shown per currency rather than being implied by one global provider or freshness label.

---

### User Story 4 - Review historical performance and trends (Priority: P2)
A user wants to understand how a currency pair has performed over the last seven or thirty days, including summary metrics, trend direction, and the provenance of both currencies used to derive every historical point. This helps the user interpret movement without mistaking mixed providers, timestamps, or freshness states for one uniform source.

**Why this priority**: Historical analysis adds depth to simple conversion and helps users understand recent market movement.

**Independent Test**: A user can choose a pair and period, identify the represented date and both rate contexts for each complete historical point, and understand the provider and freshness summary for the period.

**Acceptance Scenarios**:

1. **Given** the user opens the seven-day analytics view, **When** a supported pair has historical data, **Then** the app shows each point's represented date, derived value, and separate base- and quote-currency provider, effective date/time, freshness state, and fallback status, as well as the minimum, maximum, average, absolute change, percentage change, and trend.
2. **Given** the user opens the thirty-day analytics view, **When** a supported pair has historical data, **Then** the app shows the same point-level provenance and analytical summary for the longer period.
3. **Given** the selected pair has no available history, **When** the analytics screen loads, **Then** the app presents a clear empty-state message rather than failing.
4. **Given** a pair uses the same provider or different providers and its two rates have the same or different effective times, **When** a historical point is shown, **Then** the app identifies each rate context independently, including when one rate is live and the other is fallback or cached.
5. **Given** either required rate is unavailable for a historical date, **When** the period is displayed, **Then** the app does not present a complete derived pair value for that date, identifies the missing currency context, and excludes the incomplete point from pair statistics.
6. **Given** the selected period contains multiple providers or freshness states, **When** the analytics summary is shown, **Then** the user can identify the providers contributing on each pair side, the number of complete points included, and the presence/count of live, fallback, cached, or stale rate entries without one misleading global source or state.

---

### User Story 5 - Use the product while offline or during source failures (Priority: P2)
A user expects continued access to exchange-rate information even when the network is unstable or a rate source is unavailable. The app must continue to function using the last successful data and clearly mark it as cached or fallback data.

**Why this priority**: Reliable use during outages is essential for financial information and protects user trust.

**Independent Test**: A user can still access current currency data after a network outage if valid cached data exists and can see that the data is stale or fallback-derived.

**Acceptance Scenarios**:

1. **Given** the app cannot retrieve current data, **When** previous successful data is available, **Then** the app continues to show the last successful snapshot and marks it as cached or stale.
2. **Given** no current or cached data is available, **When** the app loads, **Then** the user receives a clear message that rates are currently unavailable.
3. **Given** a weekend or holiday rate is missing, **When** a current rate is requested, **Then** the app uses the latest valid previous rate and clearly indicates fallback usage.

---

### Edge Cases

- What happens when the user tries to convert with an unsupported currency or a blank value?
- How does the app handle a rate source outage while a cached snapshot is still available?
- What happens when a rate is missing for a holiday or weekend?
- What happens when the user changes currency input while a previous snapshot is still visible?
- How does the app behave when historical data is empty or incomplete for a selected pair?
- How are provider, effective date/time, and freshness shown per currency on current rates and All Currencies screens when a snapshot contains mixed providers or timestamps?
- How does a conversion behave when one leg is live and the other is fallback or cached?
- What does the user see when either required rate for a conversion or historical point is unavailable and no permitted fallback or cached value can supply it?
- How are same-currency conversion results associated with one applicable rate without suggesting two unrelated sources?
- How are snapshot collection/validation time, each currency rate's effective time, and a historical point's represented date distinguished?
- How does the analytics summary explain multiple providers and mixed live, fallback, cached, or stale data in terms understandable to a general user?
- How are provenance fields and freshness labels kept consistent between the web and mobile experiences?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST allow users to open the application and view current exchange-rate information without creating an account or signing in.
- **FR-002**: The product MUST support at minimum the specified fiat and cryptocurrency currencies and MUST clearly distinguish fiat currencies from cryptocurrencies.
- **FR-003**: The product MUST provide a classic converter that allows the user to enter an amount, choose source and target currencies, start conversion, and view the converted value and independent rate context for BOTH currencies used. The source-rate context MUST correspond to the selected source currency and the target-rate context to the selected target currency. For each leg, the user MUST be able to identify the currency, provider, effective date/time, freshness state (live, fallback, or cached), and whether fallback was used. The result MUST include a reference identifying the validated snapshot used. The pair rate MUST mean target-currency units per one source-currency unit and correspond to the displayed result. The product MUST NOT attribute a mixed-provider result to one provider. If either required rate has no permitted live, fallback, or cached value, the conversion MUST be unavailable and the user MUST be told which currency rate is missing.
- **FR-004**: The conversion action MUST remain unavailable until all required fields contain valid values.
- **FR-005**: The product MUST reject empty, zero, negative, and non-numeric amounts with a clear validation message that does not crash the interface.
- **FR-006**: The product MUST permit identical source and target currency conversion and MUST return the original amount without error. Its provenance MUST identify one applicable rate context for that currency and MUST NOT imply separate unrelated rate sources.
- **FR-007**: The product MUST support an All Currencies mode where users can enter one value and see all visible currencies recalculated from the same validated snapshot. For each visible currency value, the user MUST be able to identify its provider, effective date/time, freshness state, and whether fallback was used.
- **FR-008**: The product MUST ensure that all values visible together in a multi-currency comparison use one consistent validated snapshot. Individual rates within that snapshot MAY have different providers and effective times; the product MUST show those differences per currency and MUST NOT imply that the rates share one effective time.
- **FR-009**: The product MUST provide a current rates screen showing each currency code, name, current value or rate, provider, effective date/time, freshness state (live, fallback, or cached), and whether fallback was used.
- **FR-010**: The product MUST distinguish the time a complete snapshot was collected and validated from the effective date/time of each currency rate. The current rates screen MUST associate provider and effective time with each currency, not with the snapshot as a whole.
- **FR-011**: The product MUST allow the user to refresh available rate data.
- **FR-012**: The product MUST provide historical analytics for both the last 7 days and the last 30 days for supported currency pairs.
- **FR-013**: The product MUST display time-series values, minimum, maximum, average, absolute change, percentage change, and a trend indication of Growth, Decline, or Unchanged for both 7-day and 30-day periods. The summary MUST identify distinct contributing providers separately for the base and quote currencies and summarize freshness across the rate entries used. It MUST identify mixed live, fallback, cached, or stale data and MUST NOT claim that the entire period has one provider or one freshness state. Provider lists MUST be distinct provider names; `point_count` MUST count complete pair points included; live/fallback/cached counts MUST count the single freshness state assigned to each rate entry across both legs of those points; and fallback count MUST count entries whose separate fallback-used flag is true.
- **FR-014**: For every historical pair point, the product MUST expose the represented point date and the separate currency, provider, effective date/time, freshness state, and fallback-used status for BOTH rates used to derive the value. The base-rate context MUST correspond to the selected base currency and the quote-rate context to the selected quote currency. Each point MUST include a reference identifying the validated snapshot used. This MUST cover same-provider and mixed-provider pairs, different effective times, and one leg being live while the other is fallback or cached. If either required rate is unavailable and no permitted fallback or cached value can supply it, the product MUST identify the incomplete/unavailable point and MUST NOT present it as a complete derived pair value or include it in pair statistics.
- **FR-015**: The product MUST keep the app usable during network loss or source failures by using previously successful cached data when available.
- **FR-016**: The product MUST clearly mark cached or stale data and keep the original rate date or last successful update time visible.
- **FR-017**: The product MUST keep previously cached data available after restart when it exists.
- **FR-018**: The product MUST show a clear message when no usable current, permitted fallback, or cached rate is available. If one required currency rate is unavailable, the product MUST identify that currency and MUST NOT show a complete conversion or historical pair value using incomplete inputs.
- **FR-019**: The product MUST use the latest valid previous rate when a daily fiat source is missing for a weekend or holiday and MUST label fallback use for that currency rate. The displayed effective date/time MUST remain the date/time of the reused rate, not the date on which it was requested.
- **FR-020**: The product MUST maintain data consistency by using one complete validated snapshot for each conversion or set of values shown together. Rates within that snapshot MAY have different providers and effective times; the product MUST expose each rate's effective time and MUST NOT imply that snapshot membership means identical update or effective times.
- **FR-021**: The product MUST refresh visible data only after a complete new snapshot has been obtained and validated. The snapshot collection/validation time MUST be distinguishable from each individual currency rate's effective time and from the date represented by a historical pair point.
- **FR-022**: The product MUST provide the same essential capabilities and provenance meanings in web and mobile experiences: classic conversion, all-currency conversion, current rates, 7-day analytics, 30-day analytics, per-currency date/source/freshness visibility, fallback/cached/stale distinctions, and understandable unavailable-data messages.
- **FR-023**: The product MUST remain usable on an Android phone-sized mobile display.
- **FR-024**: The product MUST be understandable to a general user without requiring technical knowledge or account access. User-facing labels MUST explain live, fallback, cached, and stale in plain language: live is the latest accepted rate from its provider; fallback is a prior valid rate used because the expected rate is unavailable; cached is a previously successful rate shown because current data is unavailable; stale means the rate is older than the freshness window appropriate to its source. Stale MAY apply to cached or fallback data and MUST NOT be presented as a separate provider.
- **FR-025**: The product MUST provide user-friendly error and freshness messages. Live, fallback, and cached MUST have consistent meanings on current-rate rows, conversion legs, historical points, and analytics summaries. Each rate entry MUST have one freshness state; fallback-used MUST be a separate flag indicating rate substitution. Provider, effective time, freshness state, and fallback-used status MUST be identifiable per rate leg or currency. Cached data MUST retain its original effective time; stale MUST be indicated separately when applicable and MAY apply to cached or fallback rates. Analytics summaries MUST describe mixed provider/freshness data in language understandable to a general user.
- **FR-026**: The product MUST explicitly exclude user accounts, authentication, money transfers, wallet functions, portfolio management, and financial transaction processing from the first version scope.

### Key Entities *(include if feature involves data)*

- **Currency**: A supported monetary unit or digital asset, identified by code and type, such as fiat or cryptocurrency.
- **Rate Snapshot**: A set of currency-rate entries collected and validated together. Its collection/validation time is distinct from each entry's effective date/time; entries may have different providers and freshness states.
- **Rate Entry**: The rate for one currency, including provider, effective date/time, live/fallback/cached state, and whether fallback was used. Stale is a freshness condition, not a provider.
- **Conversion Request**: A user action that includes an amount, source currency, target currency, and validation state.
- **Conversion Result**: The converted amount and the independent rate context for each currency used. For same-currency conversion, the context identifies one applicable rate.
- **Historical Series**: Derived pair values over time. Each complete point has a represented date and the independent rate context for both currencies used.
- **Analytics Summary**: A period-based summary that includes minimum, maximum, average, absolute change, percentage change, trend direction, contributing providers by pair side, and freshness counts for the rate entries used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete a standard conversion flow in under 30 seconds without account creation, authentication, or technical setup.
- **SC-002**: Valid conversions produce consistent results in both classic and all-currencies modes for the same snapshot and supported pair.
- **SC-003**: Invalid input never produces a conversion result and the user receives clear feedback in the interface.
- **SC-004**: Same-currency conversions preserve the original entered amount exactly as expected.
- **SC-005**: For every current-rate row, conversion result, and complete historical pair point, users can identify the currency, provider, effective date/time, and live/fallback/cached state for each rate leg without inspecting technical details, including mixed-provider pairs.
- **SC-006**: Cached and fallback data are never presented as live; when only one rate leg is cached or fallback-derived, users can distinguish its status from the other leg.
- **SC-007**: Users can access both seven-day and thirty-day analytics, interpret trend direction, identify providers contributing to each pair side, and recognize mixed freshness or stale entries in the selected period.
- **SC-008**: Network failure does not terminate the application and previously cached data remains usable after restart.
- **SC-009**: Users can distinguish live, fallback, cached, and stale information on current rates, conversion results, historical points, and period summaries; snapshot collection/validation time is not confused with per-rate effective time or historical point date.
- **SC-010**: In a representative review of five conversion and analytics scenarios, users unfamiliar with currency data can correctly identify the provider and freshness of both rate legs in at least four scenarios without technical explanation.
- **SC-011**: When either required rate is unavailable and no permitted fallback or cached value can supply it, no complete conversion or historical pair value is shown, and the unavailable currency is identified.
- **SC-012**: Equivalent data scenarios in web and mobile expose the same provenance fields and use the same meanings for live, fallback, cached, and stale labels.

## Assumptions

- Users are primarily seeking quick and understandable exchange-rate information rather than financial trading capability.
- The product must support both informational consumption and comparison use cases without requiring a sign-in flow.
- Historical data may be incomplete for some periods or currencies, and product behavior should remain understandable rather than failing abruptly.
- Users expect consistent experience and behavior across web and mobile surfaces, even if layout and styling adapt to device size.
- Cached and fallback states are expected to be visible to users so they can assess freshness without ambiguity.
- The freshness window used to describe a rate as stale is appropriate to the expected update cadence of its source and is explained to users in plain language.
