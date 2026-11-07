// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Romanian Moldavian Moldovan (`ro`).
class AppLocalizationsRo extends AppLocalizations {
  AppLocalizationsRo([String locale = 'ro']) : super(locale);

  @override
  String get appName => 'CurrencyHub';

  @override
  String get navCurrentRates => 'Cursuri actuale';

  @override
  String get navAllCurrencies => 'Toate valutele';

  @override
  String get navConverter => 'Convertor';

  @override
  String get navAnalytics => 'Analiză';

  @override
  String get language => 'Limbă';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageRomanian => 'Română';

  @override
  String get languageRussian => 'Русский';

  @override
  String get languageSaveFailed => 'Preferința de limbă nu a putut fi salvată.';

  @override
  String get filterAll => 'Toate';

  @override
  String get filterFiat => 'Fiat';

  @override
  String get filterCrypto => 'Cripto';

  @override
  String get freshnessLive => 'Actual';

  @override
  String get freshnessFallback => 'Rezervă';

  @override
  String get freshnessCached => 'Din cache';

  @override
  String get freshnessStale => 'Expirat';

  @override
  String get fallbackUsed => 'S-a folosit cursul de rezervă';

  @override
  String get showMore => 'Arată mai mult';

  @override
  String get showLess => 'Arată mai puțin';

  @override
  String get provider => 'Furnizor';

  @override
  String get providerType => 'Tipul furnizorului';

  @override
  String get rateEffective => 'Curs valabil din';

  @override
  String get nominalUnit => 'Unitate nominală';

  @override
  String get snapshot => 'Instantaneu';

  @override
  String get snapshotCollected => 'Date colectate la';

  @override
  String get eachRateEffectiveTime =>
      'Fiecare curs are propria dată de valabilitate.';

  @override
  String get retry => 'Reîncearcă';

  @override
  String get searchCurrencies => 'Caută valute';

  @override
  String get searchCodeOrName => 'Caută după cod sau nume';

  @override
  String get noSearchResults => 'Nu s-au găsit valute.';

  @override
  String get clearSearch => 'Șterge căutarea';

  @override
  String get currentRates => 'Cursuri actuale';

  @override
  String get loadingCurrentRates => 'Se încarcă cursurile actuale…';

  @override
  String get currentRatesUnavailable =>
      'Cursurile actuale nu sunt disponibile.';

  @override
  String get noCurrenciesMatch => 'Nicio valută nu corespunde căutării.';

  @override
  String get rateToMdl => 'Curs în MDL';

  @override
  String get allCurrencies => 'Toate valutele';

  @override
  String get compareCurrencies => 'Compară valutele';

  @override
  String get comparisonDescription =>
      'Compară valorile folosind același instantaneu validat.';

  @override
  String get amount => 'Sumă';

  @override
  String get entryCurrency => 'Valută de referință';

  @override
  String get selectEntryCurrency => 'Selectează o valută acceptată.';

  @override
  String get loadingComparison => 'Se încarcă comparația…';

  @override
  String get comparisonUnavailable =>
      'Comparația nu este disponibilă. Este necesar un instantaneu complet al cursurilor.';

  @override
  String get rateDetailsOnEachResult =>
      'Detaliile cursului sunt disponibile pentru fiecare rezultat.';

  @override
  String get noCurrenciesMatchFilter =>
      'Nicio altă valută nu corespunde filtrului.';

  @override
  String get validPositiveAmount => 'Introdu o sumă zecimală pozitivă validă.';

  @override
  String get amountGreaterThanZero =>
      'Suma trebuie să fie mai mare decât zero.';

  @override
  String get currencyConverter => 'Convertor valutar';

  @override
  String get convertOneAmount => 'Convertește o sumă';

  @override
  String get latestValidatedSnapshot =>
      'Se folosește cel mai recent instantaneu validat.';

  @override
  String get amountExample => 'de ex. 123.45';

  @override
  String get from => 'Din';

  @override
  String get to => 'În';

  @override
  String get convert => 'Convertește';

  @override
  String get converting => 'Se convertește…';

  @override
  String get loadingCurrencies => 'Se încarcă valutele acceptate…';

  @override
  String get noSupportedCurrencies => 'Nu există valute acceptate disponibile.';

  @override
  String get supportedCurrenciesUnavailable =>
      'Lista valutelor acceptate nu este disponibilă.';

  @override
  String get positiveDecimalAmount => 'Introdu o sumă zecimală pozitivă.';

  @override
  String get conversionUnavailable =>
      'Conversia nu este disponibilă momentan. Încearcă din nou mai târziu.';

  @override
  String get conversionFailed =>
      'Conversia nu a putut fi efectuată. Încearcă din nou.';

  @override
  String get invalidConversionInput =>
      'Introdu o sumă validă și selectează valute acceptate.';

  @override
  String requiredRateUnavailable(String currency) {
    return 'Cursul pentru $currency nu este disponibil.';
  }

  @override
  String get requiredCurrencyRateUnavailable =>
      'Cursul unei valute necesare nu este disponibil.';

  @override
  String get conversionResult => 'Rezultatul conversiei';

  @override
  String get rateStatus => 'Starea cursului';

  @override
  String sourceCurrency(String currency) {
    return '$currency sursă';
  }

  @override
  String targetCurrency(String currency) {
    return '$currency destinație';
  }

  @override
  String get pairRateDescription =>
      'Cursul perechii arată câte unități din valuta destinație valorează o unitate din valuta sursă.';

  @override
  String rateContext(String label, String currency) {
    return 'Detalii curs $label — $currency';
  }

  @override
  String get source => 'Sursă';

  @override
  String get target => 'Destinație';

  @override
  String get rateAnalytics => 'Analiza cursurilor';

  @override
  String get historicalAnalytics => 'Analiză istorică';

  @override
  String get analyticsDescription =>
      'Explorează evoluția cursului și sursele datelor.';

  @override
  String get baseCurrency => 'Valută de bază';

  @override
  String get quoteCurrency => 'Valută cotată';

  @override
  String get sevenDays => '7 zile';

  @override
  String get thirtyDays => '30 de zile';

  @override
  String get loadingAnalytics => 'Se încarcă analiza istorică…';

  @override
  String get analyticsUnavailable => 'Analiza nu este disponibilă.';

  @override
  String get noHistoricalData =>
      'Nu există date istorice pentru această pereche în perioada selectată.';

  @override
  String get rateHistory => 'Istoricul cursului';

  @override
  String get selectedDay => 'Zi selectată';

  @override
  String get base => 'Bază';

  @override
  String get quote => 'Cotare';

  @override
  String get minimum => 'Minim';

  @override
  String get maximum => 'Maxim';

  @override
  String get average => 'Medie';

  @override
  String get absoluteChange => 'Variație absolută';

  @override
  String get percentageChange => 'Variație procentuală';

  @override
  String get trend => 'Tendință';

  @override
  String get growth => 'Creștere';

  @override
  String get decline => 'Scădere';

  @override
  String get unchanged => 'Neschimbat';

  @override
  String get dataContext => 'Contextul datelor';

  @override
  String baseProviders(String providers) {
    return 'Furnizori pentru bază: $providers';
  }

  @override
  String quoteProviders(String providers) {
    return 'Furnizori pentru cotare: $providers';
  }

  @override
  String liveCount(int count) {
    return 'Actuale: $count';
  }

  @override
  String fallbackCount(int count) {
    return 'De rezervă: $count';
  }

  @override
  String cachedCount(int count) {
    return 'Din cache: $count';
  }

  @override
  String staleCount(int count) {
    return 'Expirate: $count';
  }

  @override
  String fallbackUsedCount(int count) {
    return 'Cursuri de rezervă folosite: $count';
  }

  @override
  String baseCurrencyContext(String currency) {
    return 'Valută de bază — $currency';
  }

  @override
  String quoteCurrencyContext(String currency) {
    return 'Valută cotată — $currency';
  }
}
