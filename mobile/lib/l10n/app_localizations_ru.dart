// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'CurrencyHub';

  @override
  String get navCurrentRates => 'Текущие курсы';

  @override
  String get navAllCurrencies => 'Все валюты';

  @override
  String get navConverter => 'Конвертер';

  @override
  String get navAnalytics => 'Аналитика';

  @override
  String get language => 'Язык';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageRomanian => 'Română';

  @override
  String get languageRussian => 'Русский';

  @override
  String get languageSaveFailed => 'Не удалось сохранить выбранный язык.';

  @override
  String get filterAll => 'Все';

  @override
  String get filterFiat => 'Фиатные';

  @override
  String get filterCrypto => 'Криптовалюты';

  @override
  String get freshnessLive => 'Актуальный';

  @override
  String get freshnessFallback => 'Резервный';

  @override
  String get freshnessCached => 'Из кэша';

  @override
  String get freshnessStale => 'Устаревший';

  @override
  String get fallbackUsed => 'Использован резервный курс';

  @override
  String get showMore => 'Подробнее';

  @override
  String get showLess => 'Свернуть';

  @override
  String get provider => 'Поставщик';

  @override
  String get providerType => 'Тип поставщика';

  @override
  String get rateEffective => 'Курс действует с';

  @override
  String get nominalUnit => 'Номинал';

  @override
  String get snapshot => 'Снимок данных';

  @override
  String get snapshotCollected => 'Данные собраны';

  @override
  String get eachRateEffectiveTime =>
      'Для каждого курса указано своё время действия.';

  @override
  String get retry => 'Повторить';

  @override
  String get searchCurrencies => 'Поиск валют';

  @override
  String get searchCodeOrName => 'Поиск по коду или названию';

  @override
  String get noSearchResults => 'Валюты не найдены.';

  @override
  String get clearSearch => 'Очистить поиск';

  @override
  String get currentRates => 'Текущие курсы';

  @override
  String get loadingCurrentRates => 'Загрузка текущих курсов…';

  @override
  String get currentRatesUnavailable => 'Текущие курсы недоступны.';

  @override
  String get noCurrenciesMatch => 'По запросу валюты не найдены.';

  @override
  String get rateToMdl => 'Курс к MDL';

  @override
  String get allCurrencies => 'Все валюты';

  @override
  String get compareCurrencies => 'Сравнение валют';

  @override
  String get comparisonDescription =>
      'Сравнивайте значения по одному проверенному снимку курсов.';

  @override
  String get amount => 'Сумма';

  @override
  String get entryCurrency => 'Исходная валюта';

  @override
  String get selectEntryCurrency => 'Выберите поддерживаемую исходную валюту.';

  @override
  String get loadingComparison => 'Загрузка сравнения валют…';

  @override
  String get comparisonUnavailable =>
      'Сравнение недоступно. Нужен полный снимок курсов.';

  @override
  String get rateDetailsOnEachResult =>
      'Подробности курса доступны для каждой валюты.';

  @override
  String get noCurrenciesMatchFilter =>
      'Нет других валют, подходящих под фильтр.';

  @override
  String get validPositiveAmount => 'Введите корректную положительную сумму.';

  @override
  String get amountGreaterThanZero => 'Сумма должна быть больше нуля.';

  @override
  String get currencyConverter => 'Конвертер валют';

  @override
  String get convertOneAmount => 'Конвертация суммы';

  @override
  String get latestValidatedSnapshot =>
      'Используется последний проверенный снимок курсов.';

  @override
  String get amountExample => 'например, 123.45';

  @override
  String get from => 'Из';

  @override
  String get to => 'В';

  @override
  String get convert => 'Конвертировать';

  @override
  String get converting => 'Конвертация…';

  @override
  String get loadingCurrencies => 'Загрузка поддерживаемых валют…';

  @override
  String get noSupportedCurrencies => 'Нет доступных поддерживаемых валют.';

  @override
  String get supportedCurrenciesUnavailable =>
      'Список поддерживаемых валют недоступен.';

  @override
  String get positiveDecimalAmount => 'Введите положительную сумму.';

  @override
  String get conversionUnavailable =>
      'Конвертация сейчас недоступна. Попробуйте позже.';

  @override
  String get conversionFailed =>
      'Не удалось выполнить конвертацию. Попробуйте ещё раз.';

  @override
  String get invalidConversionInput =>
      'Введите корректную сумму и выберите поддерживаемые валюты.';

  @override
  String requiredRateUnavailable(String currency) {
    return 'Курс валюты $currency недоступен.';
  }

  @override
  String get requiredCurrencyRateUnavailable =>
      'Необходимый валютный курс недоступен.';

  @override
  String get conversionResult => 'Результат конвертации';

  @override
  String get rateStatus => 'Статус курса';

  @override
  String sourceCurrency(String currency) {
    return 'Исходная $currency';
  }

  @override
  String targetCurrency(String currency) {
    return 'Целевая $currency';
  }

  @override
  String get pairRateDescription =>
      'Курс пары показывает количество единиц целевой валюты за одну единицу исходной.';

  @override
  String rateContext(String label, String currency) {
    return 'Данные курса ($label) — $currency';
  }

  @override
  String get source => 'Исходная';

  @override
  String get target => 'Целевая';

  @override
  String get rateAnalytics => 'Аналитика курсов';

  @override
  String get historicalAnalytics => 'История курсов';

  @override
  String get analyticsDescription =>
      'Изучайте динамику курсов и источники данных.';

  @override
  String get baseCurrency => 'Базовая валюта';

  @override
  String get quoteCurrency => 'Котируемая валюта';

  @override
  String get sevenDays => '7 дней';

  @override
  String get thirtyDays => '30 дней';

  @override
  String get loadingAnalytics => 'Загрузка исторической аналитики…';

  @override
  String get analyticsUnavailable => 'Аналитика недоступна.';

  @override
  String get noHistoricalData =>
      'За выбранный период нет исторических данных по этой паре.';

  @override
  String get rateHistory => 'История курса';

  @override
  String get selectedDay => 'Выбранный день';

  @override
  String get base => 'Базовая';

  @override
  String get quote => 'Котируемая';

  @override
  String get minimum => 'Минимум';

  @override
  String get maximum => 'Максимум';

  @override
  String get average => 'Среднее';

  @override
  String get absoluteChange => 'Абсолютное изменение';

  @override
  String get percentageChange => 'Изменение в процентах';

  @override
  String get trend => 'Тенденция';

  @override
  String get growth => 'Рост';

  @override
  String get decline => 'Снижение';

  @override
  String get unchanged => 'Без изменений';

  @override
  String get dataContext => 'Источники данных';

  @override
  String baseProviders(String providers) {
    return 'Поставщики базовой валюты: $providers';
  }

  @override
  String quoteProviders(String providers) {
    return 'Поставщики котируемой валюты: $providers';
  }

  @override
  String liveCount(int count) {
    return 'Актуальные: $count';
  }

  @override
  String fallbackCount(int count) {
    return 'Резервные: $count';
  }

  @override
  String cachedCount(int count) {
    return 'Из кэша: $count';
  }

  @override
  String staleCount(int count) {
    return 'Устаревшие: $count';
  }

  @override
  String fallbackUsedCount(int count) {
    return 'Использовано резервных курсов: $count';
  }

  @override
  String baseCurrencyContext(String currency) {
    return 'Базовая валюта — $currency';
  }

  @override
  String quoteCurrencyContext(String currency) {
    return 'Котируемая валюта — $currency';
  }
}
