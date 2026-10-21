# Quickstart Validation Guide

## Purpose

This guide describes the minimum validation scenarios needed to confirm the product behavior described in the specification. It is not an implementation guide; it is a validation checklist for the product team and test engineers.

## Prerequisites

- Access to a working environment containing the web and mobile clients and the shared API backend.
- A valid source of current rate data and a stored historical dataset.
- A mechanism for simulating network interruption or provider failure.
- Test data covering at least the required fiat and crypto currency set.

## Validation Scenarios

### 1. Open the app without sign-in

1. Launch the web or mobile application.
2. Confirm the app opens without account creation or authentication.
3. Verify that supported currencies are visible with rate information.
4. Confirm the UI shows source and freshness metadata.

Expected outcome: The user can access the essential conversion and rate information without onboarding.

### 2. Classic conversion

1. Enter a valid numeric amount.
2. Choose a source and target currency.
3. Trigger conversion.
4. Verify the result, rate date, and source are shown.

Expected outcome: Conversion succeeds and exposes the exact rate context used.

### 3. Validation failures

1. Submit blank, zero, negative, and non-numeric inputs.
2. Observe the conversion action and validation messages.

Expected outcome: No conversion is produced and the user receives a clear explanation.

### 4. Same-currency conversion

1. Choose the same currency for source and target.
2. Submit the conversion.

Expected outcome: The value returned matches the original amount exactly.

### 5. Multi-currency comparison

1. Open the all-currencies view.
2. Enter a value in one currency field.
3. Observe the recalculated values in all other visible currencies.

Expected outcome: Values are recalculated from one consistent snapshot and remain synchronized.

### 6. Cached and fallback data

1. Simulate a rate-source failure or offline state.
2. Confirm cached last-successful data appears with a stale or cached label.
3. Simulate a missing weekend or holiday rate.
4. Confirm the last valid previous rate is used and marked as fallback data.

Expected outcome: The app remains usable and clearly communicates freshness and fallback status.

### 7. Analytics validation

1. Open the 7-day analytics view for a supported pair.
2. Review the time series and summary values.
3. Repeat for the 30-day view.
4. Check trend labeling and summary calculations.

Expected outcome: Minimum, maximum, average, absolute change, percentage change, and trend are visible and directionally accurate.

### 8. Empty-state behavior

1. Select a pair with no history.
2. Open the analytics screen.

Expected outcome: The screen displays a clear empty-state message instead of failing or showing misleading numbers.

### 9. Restart continuity

1. Load valid rate data.
2. Restart the application with the network unavailable.
3. Confirm the cached data remains visible.

Expected outcome: Previously cached data remains usable after restart.

### 10. Shared product consistency

1. Validate the same scenario in the web app and the mobile app.
2. Compare the essential features and data freshness labels.

Expected outcome: Both clients provide the same essential behavior, with only layout differences by screen size and platform.
