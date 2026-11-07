// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'CurrencyHub';

  @override
  String get navCurrentRates => 'Current Rates';

  @override
  String get navAllCurrencies => 'All Currencies';

  @override
  String get navConverter => 'Converter';

  @override
  String get navAnalytics => 'Analytics';

  @override
  String get language => 'Language';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageRomanian => 'Română';

  @override
  String get languageRussian => 'Русский';

  @override
  String get languageSaveFailed => 'Could not save your language preference.';

  @override
  String get filterAll => 'All';

  @override
  String get filterFiat => 'Fiat';

  @override
  String get filterCrypto => 'Crypto';

  @override
  String get freshnessLive => 'Live';

  @override
  String get freshnessFallback => 'Fallback';

  @override
  String get freshnessCached => 'Cached';

  @override
  String get freshnessStale => 'Stale';

  @override
  String get fallbackUsed => 'Fallback used';

  @override
  String get showMore => 'Show more';

  @override
  String get showLess => 'Show less';

  @override
  String get provider => 'Provider';

  @override
  String get providerType => 'Provider type';

  @override
  String get rateEffective => 'Rate effective';

  @override
  String get nominalUnit => 'Nominal unit';

  @override
  String get snapshot => 'Snapshot';

  @override
  String get snapshotCollected => 'Snapshot collected';

  @override
  String get eachRateEffectiveTime => 'Each rate has its own effective time.';

  @override
  String get retry => 'Retry';

  @override
  String get searchCurrencies => 'Search currencies';

  @override
  String get searchCodeOrName => 'Search by code or name';

  @override
  String get noSearchResults => 'No matching currencies.';

  @override
  String get clearSearch => 'Clear search';

  @override
  String get currentRates => 'Current Rates';

  @override
  String get loadingCurrentRates => 'Loading current rates…';

  @override
  String get currentRatesUnavailable => 'Current rates are unavailable.';

  @override
  String get noCurrenciesMatch => 'No currencies match your search.';

  @override
  String get rateToMdl => 'Rate to MDL';

  @override
  String get allCurrencies => 'All Currencies';

  @override
  String get compareCurrencies => 'Compare currencies';

  @override
  String get comparisonDescription =>
      'Compare values using one validated rate snapshot.';

  @override
  String get amount => 'Amount';

  @override
  String get entryCurrency => 'Entry currency';

  @override
  String get selectEntryCurrency => 'Select a supported entry currency.';

  @override
  String get loadingComparison => 'Loading currency comparison…';

  @override
  String get comparisonUnavailable =>
      'Comparison is unavailable. A complete rate snapshot is required.';

  @override
  String get rateDetailsOnEachResult =>
      'Rate details are available for each result.';

  @override
  String get noCurrenciesMatchFilter =>
      'No other currencies match this filter.';

  @override
  String get validPositiveAmount => 'Enter a valid positive decimal amount.';

  @override
  String get amountGreaterThanZero => 'Amount must be greater than zero.';

  @override
  String get currencyConverter => 'Currency Converter';

  @override
  String get convertOneAmount => 'Convert one amount';

  @override
  String get latestValidatedSnapshot =>
      'Using the latest validated rate snapshot.';

  @override
  String get amountExample => 'e.g. 123.45';

  @override
  String get from => 'From';

  @override
  String get to => 'To';

  @override
  String get convert => 'Convert';

  @override
  String get converting => 'Converting…';

  @override
  String get loadingCurrencies => 'Loading supported currencies…';

  @override
  String get noSupportedCurrencies => 'No supported currencies are available.';

  @override
  String get supportedCurrenciesUnavailable =>
      'Supported currencies are unavailable.';

  @override
  String get positiveDecimalAmount => 'Enter a positive decimal amount.';

  @override
  String get conversionUnavailable =>
      'Conversion is currently unavailable. Try again later.';

  @override
  String get conversionFailed =>
      'Conversion could not be completed. Please try again.';

  @override
  String get invalidConversionInput =>
      'Enter a valid amount and select supported currencies.';

  @override
  String requiredRateUnavailable(String currency) {
    return 'The rate for $currency is unavailable.';
  }

  @override
  String get requiredCurrencyRateUnavailable =>
      'A required currency rate is unavailable.';

  @override
  String get conversionResult => 'Conversion result';

  @override
  String get rateStatus => 'Rate status';

  @override
  String sourceCurrency(String currency) {
    return 'Source $currency';
  }

  @override
  String targetCurrency(String currency) {
    return 'Target $currency';
  }

  @override
  String get pairRateDescription =>
      'The pair rate shows target-currency units for one source-currency unit.';

  @override
  String rateContext(String label, String currency) {
    return '$label rate context — $currency';
  }

  @override
  String get source => 'Source';

  @override
  String get target => 'Target';

  @override
  String get rateAnalytics => 'Rate Analytics';

  @override
  String get historicalAnalytics => 'Historical Analytics';

  @override
  String get analyticsDescription =>
      'Explore rate movements and their sources.';

  @override
  String get baseCurrency => 'Base currency';

  @override
  String get quoteCurrency => 'Quote currency';

  @override
  String get sevenDays => '7 days';

  @override
  String get thirtyDays => '30 days';

  @override
  String get loadingAnalytics => 'Loading historical analytics…';

  @override
  String get analyticsUnavailable => 'Analytics are unavailable.';

  @override
  String get noHistoricalData =>
      'No historical data is available for this pair in the selected period.';

  @override
  String get rateHistory => 'Rate history';

  @override
  String get selectedDay => 'Selected day';

  @override
  String get base => 'Base';

  @override
  String get quote => 'Quote';

  @override
  String get minimum => 'Minimum';

  @override
  String get maximum => 'Maximum';

  @override
  String get average => 'Average';

  @override
  String get absoluteChange => 'Absolute change';

  @override
  String get percentageChange => 'Percentage change';

  @override
  String get trend => 'Trend';

  @override
  String get growth => 'Growth';

  @override
  String get decline => 'Decline';

  @override
  String get unchanged => 'Unchanged';

  @override
  String get dataContext => 'Data context';

  @override
  String baseProviders(String providers) {
    return 'Base: $providers';
  }

  @override
  String quoteProviders(String providers) {
    return 'Quote: $providers';
  }

  @override
  String liveCount(int count) {
    return 'Live: $count';
  }

  @override
  String fallbackCount(int count) {
    return 'Fallback: $count';
  }

  @override
  String cachedCount(int count) {
    return 'Cached: $count';
  }

  @override
  String staleCount(int count) {
    return 'Stale: $count';
  }

  @override
  String fallbackUsedCount(int count) {
    return 'Fallback used: $count';
  }

  @override
  String baseCurrencyContext(String currency) {
    return 'Base currency — $currency';
  }

  @override
  String quoteCurrencyContext(String currency) {
    return 'Quote currency — $currency';
  }
}
