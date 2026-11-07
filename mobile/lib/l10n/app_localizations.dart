import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ro.dart';
import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ro'),
    Locale('ru'),
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'CurrencyHub'**
  String get appName;

  /// No description provided for @navCurrentRates.
  ///
  /// In en, this message translates to:
  /// **'Current Rates'**
  String get navCurrentRates;

  /// No description provided for @navAllCurrencies.
  ///
  /// In en, this message translates to:
  /// **'All Currencies'**
  String get navAllCurrencies;

  /// No description provided for @navConverter.
  ///
  /// In en, this message translates to:
  /// **'Converter'**
  String get navConverter;

  /// No description provided for @navAnalytics.
  ///
  /// In en, this message translates to:
  /// **'Analytics'**
  String get navAnalytics;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @languageRomanian.
  ///
  /// In en, this message translates to:
  /// **'Română'**
  String get languageRomanian;

  /// No description provided for @languageRussian.
  ///
  /// In en, this message translates to:
  /// **'Русский'**
  String get languageRussian;

  /// No description provided for @languageSaveFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not save your language preference.'**
  String get languageSaveFailed;

  /// No description provided for @filterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get filterAll;

  /// No description provided for @filterFiat.
  ///
  /// In en, this message translates to:
  /// **'Fiat'**
  String get filterFiat;

  /// No description provided for @filterCrypto.
  ///
  /// In en, this message translates to:
  /// **'Crypto'**
  String get filterCrypto;

  /// No description provided for @freshnessLive.
  ///
  /// In en, this message translates to:
  /// **'Live'**
  String get freshnessLive;

  /// No description provided for @freshnessFallback.
  ///
  /// In en, this message translates to:
  /// **'Fallback'**
  String get freshnessFallback;

  /// No description provided for @freshnessCached.
  ///
  /// In en, this message translates to:
  /// **'Cached'**
  String get freshnessCached;

  /// No description provided for @freshnessStale.
  ///
  /// In en, this message translates to:
  /// **'Stale'**
  String get freshnessStale;

  /// No description provided for @fallbackUsed.
  ///
  /// In en, this message translates to:
  /// **'Fallback used'**
  String get fallbackUsed;

  /// No description provided for @showMore.
  ///
  /// In en, this message translates to:
  /// **'Show more'**
  String get showMore;

  /// No description provided for @showLess.
  ///
  /// In en, this message translates to:
  /// **'Show less'**
  String get showLess;

  /// No description provided for @provider.
  ///
  /// In en, this message translates to:
  /// **'Provider'**
  String get provider;

  /// No description provided for @providerType.
  ///
  /// In en, this message translates to:
  /// **'Provider type'**
  String get providerType;

  /// No description provided for @rateEffective.
  ///
  /// In en, this message translates to:
  /// **'Rate effective'**
  String get rateEffective;

  /// No description provided for @nominalUnit.
  ///
  /// In en, this message translates to:
  /// **'Nominal unit'**
  String get nominalUnit;

  /// No description provided for @snapshot.
  ///
  /// In en, this message translates to:
  /// **'Snapshot'**
  String get snapshot;

  /// No description provided for @snapshotCollected.
  ///
  /// In en, this message translates to:
  /// **'Snapshot collected'**
  String get snapshotCollected;

  /// No description provided for @eachRateEffectiveTime.
  ///
  /// In en, this message translates to:
  /// **'Each rate has its own effective time.'**
  String get eachRateEffectiveTime;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @searchCurrencies.
  ///
  /// In en, this message translates to:
  /// **'Search currencies'**
  String get searchCurrencies;

  /// No description provided for @searchCodeOrName.
  ///
  /// In en, this message translates to:
  /// **'Search by code or name'**
  String get searchCodeOrName;

  /// No description provided for @noSearchResults.
  ///
  /// In en, this message translates to:
  /// **'No matching currencies.'**
  String get noSearchResults;

  /// No description provided for @clearSearch.
  ///
  /// In en, this message translates to:
  /// **'Clear search'**
  String get clearSearch;

  /// No description provided for @currentRates.
  ///
  /// In en, this message translates to:
  /// **'Current Rates'**
  String get currentRates;

  /// No description provided for @loadingCurrentRates.
  ///
  /// In en, this message translates to:
  /// **'Loading current rates…'**
  String get loadingCurrentRates;

  /// No description provided for @currentRatesUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Current rates are unavailable.'**
  String get currentRatesUnavailable;

  /// No description provided for @noCurrenciesMatch.
  ///
  /// In en, this message translates to:
  /// **'No currencies match your search.'**
  String get noCurrenciesMatch;

  /// No description provided for @rateToMdl.
  ///
  /// In en, this message translates to:
  /// **'Rate to MDL'**
  String get rateToMdl;

  /// No description provided for @allCurrencies.
  ///
  /// In en, this message translates to:
  /// **'All Currencies'**
  String get allCurrencies;

  /// No description provided for @compareCurrencies.
  ///
  /// In en, this message translates to:
  /// **'Compare currencies'**
  String get compareCurrencies;

  /// No description provided for @comparisonDescription.
  ///
  /// In en, this message translates to:
  /// **'Compare values using one validated rate snapshot.'**
  String get comparisonDescription;

  /// No description provided for @amount.
  ///
  /// In en, this message translates to:
  /// **'Amount'**
  String get amount;

  /// No description provided for @entryCurrency.
  ///
  /// In en, this message translates to:
  /// **'Entry currency'**
  String get entryCurrency;

  /// No description provided for @selectEntryCurrency.
  ///
  /// In en, this message translates to:
  /// **'Select a supported entry currency.'**
  String get selectEntryCurrency;

  /// No description provided for @loadingComparison.
  ///
  /// In en, this message translates to:
  /// **'Loading currency comparison…'**
  String get loadingComparison;

  /// No description provided for @comparisonUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Comparison is unavailable. A complete rate snapshot is required.'**
  String get comparisonUnavailable;

  /// No description provided for @rateDetailsOnEachResult.
  ///
  /// In en, this message translates to:
  /// **'Rate details are available for each result.'**
  String get rateDetailsOnEachResult;

  /// No description provided for @noCurrenciesMatchFilter.
  ///
  /// In en, this message translates to:
  /// **'No other currencies match this filter.'**
  String get noCurrenciesMatchFilter;

  /// No description provided for @validPositiveAmount.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid positive decimal amount.'**
  String get validPositiveAmount;

  /// No description provided for @amountGreaterThanZero.
  ///
  /// In en, this message translates to:
  /// **'Amount must be greater than zero.'**
  String get amountGreaterThanZero;

  /// No description provided for @currencyConverter.
  ///
  /// In en, this message translates to:
  /// **'Currency Converter'**
  String get currencyConverter;

  /// No description provided for @convertOneAmount.
  ///
  /// In en, this message translates to:
  /// **'Convert one amount'**
  String get convertOneAmount;

  /// No description provided for @latestValidatedSnapshot.
  ///
  /// In en, this message translates to:
  /// **'Using the latest validated rate snapshot.'**
  String get latestValidatedSnapshot;

  /// No description provided for @amountExample.
  ///
  /// In en, this message translates to:
  /// **'e.g. 123.45'**
  String get amountExample;

  /// No description provided for @from.
  ///
  /// In en, this message translates to:
  /// **'From'**
  String get from;

  /// No description provided for @to.
  ///
  /// In en, this message translates to:
  /// **'To'**
  String get to;

  /// No description provided for @convert.
  ///
  /// In en, this message translates to:
  /// **'Convert'**
  String get convert;

  /// No description provided for @converting.
  ///
  /// In en, this message translates to:
  /// **'Converting…'**
  String get converting;

  /// No description provided for @loadingCurrencies.
  ///
  /// In en, this message translates to:
  /// **'Loading supported currencies…'**
  String get loadingCurrencies;

  /// No description provided for @noSupportedCurrencies.
  ///
  /// In en, this message translates to:
  /// **'No supported currencies are available.'**
  String get noSupportedCurrencies;

  /// No description provided for @supportedCurrenciesUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Supported currencies are unavailable.'**
  String get supportedCurrenciesUnavailable;

  /// No description provided for @positiveDecimalAmount.
  ///
  /// In en, this message translates to:
  /// **'Enter a positive decimal amount.'**
  String get positiveDecimalAmount;

  /// No description provided for @conversionUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Conversion is currently unavailable. Try again later.'**
  String get conversionUnavailable;

  /// No description provided for @conversionFailed.
  ///
  /// In en, this message translates to:
  /// **'Conversion could not be completed. Please try again.'**
  String get conversionFailed;

  /// No description provided for @invalidConversionInput.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid amount and select supported currencies.'**
  String get invalidConversionInput;

  /// No description provided for @requiredRateUnavailable.
  ///
  /// In en, this message translates to:
  /// **'The rate for {currency} is unavailable.'**
  String requiredRateUnavailable(String currency);

  /// No description provided for @requiredCurrencyRateUnavailable.
  ///
  /// In en, this message translates to:
  /// **'A required currency rate is unavailable.'**
  String get requiredCurrencyRateUnavailable;

  /// No description provided for @conversionResult.
  ///
  /// In en, this message translates to:
  /// **'Conversion result'**
  String get conversionResult;

  /// No description provided for @rateStatus.
  ///
  /// In en, this message translates to:
  /// **'Rate status'**
  String get rateStatus;

  /// No description provided for @sourceCurrency.
  ///
  /// In en, this message translates to:
  /// **'Source {currency}'**
  String sourceCurrency(String currency);

  /// No description provided for @targetCurrency.
  ///
  /// In en, this message translates to:
  /// **'Target {currency}'**
  String targetCurrency(String currency);

  /// No description provided for @pairRateDescription.
  ///
  /// In en, this message translates to:
  /// **'The pair rate shows target-currency units for one source-currency unit.'**
  String get pairRateDescription;

  /// No description provided for @rateContext.
  ///
  /// In en, this message translates to:
  /// **'{label} rate context — {currency}'**
  String rateContext(String label, String currency);

  /// No description provided for @source.
  ///
  /// In en, this message translates to:
  /// **'Source'**
  String get source;

  /// No description provided for @target.
  ///
  /// In en, this message translates to:
  /// **'Target'**
  String get target;

  /// No description provided for @rateAnalytics.
  ///
  /// In en, this message translates to:
  /// **'Rate Analytics'**
  String get rateAnalytics;

  /// No description provided for @historicalAnalytics.
  ///
  /// In en, this message translates to:
  /// **'Historical Analytics'**
  String get historicalAnalytics;

  /// No description provided for @analyticsDescription.
  ///
  /// In en, this message translates to:
  /// **'Explore rate movements and their sources.'**
  String get analyticsDescription;

  /// No description provided for @baseCurrency.
  ///
  /// In en, this message translates to:
  /// **'Base currency'**
  String get baseCurrency;

  /// No description provided for @quoteCurrency.
  ///
  /// In en, this message translates to:
  /// **'Quote currency'**
  String get quoteCurrency;

  /// No description provided for @sevenDays.
  ///
  /// In en, this message translates to:
  /// **'7 days'**
  String get sevenDays;

  /// No description provided for @thirtyDays.
  ///
  /// In en, this message translates to:
  /// **'30 days'**
  String get thirtyDays;

  /// No description provided for @loadingAnalytics.
  ///
  /// In en, this message translates to:
  /// **'Loading historical analytics…'**
  String get loadingAnalytics;

  /// No description provided for @analyticsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Analytics are unavailable.'**
  String get analyticsUnavailable;

  /// No description provided for @noHistoricalData.
  ///
  /// In en, this message translates to:
  /// **'No historical data is available for this pair in the selected period.'**
  String get noHistoricalData;

  /// No description provided for @rateHistory.
  ///
  /// In en, this message translates to:
  /// **'Rate history'**
  String get rateHistory;

  /// No description provided for @selectedDay.
  ///
  /// In en, this message translates to:
  /// **'Selected day'**
  String get selectedDay;

  /// No description provided for @base.
  ///
  /// In en, this message translates to:
  /// **'Base'**
  String get base;

  /// No description provided for @quote.
  ///
  /// In en, this message translates to:
  /// **'Quote'**
  String get quote;

  /// No description provided for @minimum.
  ///
  /// In en, this message translates to:
  /// **'Minimum'**
  String get minimum;

  /// No description provided for @maximum.
  ///
  /// In en, this message translates to:
  /// **'Maximum'**
  String get maximum;

  /// No description provided for @average.
  ///
  /// In en, this message translates to:
  /// **'Average'**
  String get average;

  /// No description provided for @absoluteChange.
  ///
  /// In en, this message translates to:
  /// **'Absolute change'**
  String get absoluteChange;

  /// No description provided for @percentageChange.
  ///
  /// In en, this message translates to:
  /// **'Percentage change'**
  String get percentageChange;

  /// No description provided for @trend.
  ///
  /// In en, this message translates to:
  /// **'Trend'**
  String get trend;

  /// No description provided for @growth.
  ///
  /// In en, this message translates to:
  /// **'Growth'**
  String get growth;

  /// No description provided for @decline.
  ///
  /// In en, this message translates to:
  /// **'Decline'**
  String get decline;

  /// No description provided for @unchanged.
  ///
  /// In en, this message translates to:
  /// **'Unchanged'**
  String get unchanged;

  /// No description provided for @dataContext.
  ///
  /// In en, this message translates to:
  /// **'Data context'**
  String get dataContext;

  /// No description provided for @baseProviders.
  ///
  /// In en, this message translates to:
  /// **'Base: {providers}'**
  String baseProviders(String providers);

  /// No description provided for @quoteProviders.
  ///
  /// In en, this message translates to:
  /// **'Quote: {providers}'**
  String quoteProviders(String providers);

  /// No description provided for @liveCount.
  ///
  /// In en, this message translates to:
  /// **'Live: {count}'**
  String liveCount(int count);

  /// No description provided for @fallbackCount.
  ///
  /// In en, this message translates to:
  /// **'Fallback: {count}'**
  String fallbackCount(int count);

  /// No description provided for @cachedCount.
  ///
  /// In en, this message translates to:
  /// **'Cached: {count}'**
  String cachedCount(int count);

  /// No description provided for @staleCount.
  ///
  /// In en, this message translates to:
  /// **'Stale: {count}'**
  String staleCount(int count);

  /// No description provided for @fallbackUsedCount.
  ///
  /// In en, this message translates to:
  /// **'Fallback used: {count}'**
  String fallbackUsedCount(int count);

  /// No description provided for @baseCurrencyContext.
  ///
  /// In en, this message translates to:
  /// **'Base currency — {currency}'**
  String baseCurrencyContext(String currency);

  /// No description provided for @quoteCurrencyContext.
  ///
  /// In en, this message translates to:
  /// **'Quote currency — {currency}'**
  String quoteCurrencyContext(String currency);
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ro', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ro':
      return AppLocalizationsRo();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
