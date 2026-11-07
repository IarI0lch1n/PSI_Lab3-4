import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract interface class LocalePreferenceStore {
  Future<String?> readLocale();

  Future<void> saveLocale(String languageCode);
}

class SharedPreferencesLocalePreferenceStore implements LocalePreferenceStore {
  SharedPreferencesLocalePreferenceStore({SharedPreferencesAsync? preferences})
    : _preferences = preferences ?? SharedPreferencesAsync();

  static const storageKey = 'currencyhub:locale:v1';

  final SharedPreferencesAsync _preferences;

  @override
  Future<String?> readLocale() => _preferences.getString(storageKey);

  @override
  Future<void> saveLocale(String languageCode) =>
      _preferences.setString(storageKey, languageCode);
}

class CurrencyHubLocaleController extends ChangeNotifier {
  CurrencyHubLocaleController({LocalePreferenceStore? preferenceStore})
    : _preferenceStore =
          preferenceStore ?? SharedPreferencesLocalePreferenceStore();

  static const supportedLocales = [Locale('en'), Locale('ro'), Locale('ru')];

  final LocalePreferenceStore _preferenceStore;
  Locale? _locale;
  int _selectionVersion = 0;

  Locale? get locale => _locale;

  Future<void> restore() async {
    final versionAtStart = _selectionVersion;
    final savedLanguageCode = await _preferenceStore.readLocale();
    if (versionAtStart != _selectionVersion) return;
    if (savedLanguageCode == null) return;
    final savedLocale = _localeForLanguageCode(savedLanguageCode);
    if (savedLocale != null) {
      _locale = savedLocale;
      notifyListeners();
    }
  }

  Future<void> setLocale(Locale locale) async {
    final supportedLocale = _localeForLanguageCode(locale.languageCode);
    if (supportedLocale == null) {
      throw ArgumentError.value(locale, 'locale', 'Unsupported language.');
    }
    _selectionVersion++;
    _locale = supportedLocale;
    notifyListeners();
    await _preferenceStore.saveLocale(supportedLocale.languageCode);
  }

  static Locale resolveLocale(Locale? locale, Iterable<Locale> supported) {
    final languageCode = locale?.languageCode.toLowerCase();
    for (final candidate in supported) {
      if (candidate.languageCode == languageCode) return candidate;
    }
    return supported.firstWhere(
      (candidate) => candidate.languageCode == 'en',
      orElse: () => supported.first,
    );
  }

  static Locale? _localeForLanguageCode(String languageCode) {
    final normalizedCode = languageCode.toLowerCase();
    for (final locale in supportedLocales) {
      if (locale.languageCode == normalizedCode) return locale;
    }
    return null;
  }
}

class CurrencyHubLocaleScope extends InheritedWidget {
  const CurrencyHubLocaleScope({
    required this.controller,
    required super.child,
    super.key,
  });

  final CurrencyHubLocaleController controller;

  static CurrencyHubLocaleController? maybeOf(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<CurrencyHubLocaleScope>()
      ?.controller;

  @override
  bool updateShouldNotify(CurrencyHubLocaleScope oldWidget) =>
      controller != oldWidget.controller;
}
