import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/core/presentation/currency_hub_locale_controller.dart';
import 'package:currencyhub_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('defaults to English and exposes the language selector', (
    tester,
  ) async {
    final controller = CurrencyHubLocaleController(
      preferenceStore: _MemoryLocalePreferenceStore(),
    );
    addTearDown(controller.dispose);
    await _pumpApp(tester, controller);

    expect(find.text('Current Rates'), findsOneWidget);
    expect(find.text('Search currencies'), findsOneWidget);
    await _openDrawer(tester);
    expect(find.byKey(const Key('language-selector')), findsOneWidget);
    expect(find.text('Language'), findsOneWidget);
    expect(find.text('English'), findsOneWidget);
  });

  testWidgets('renders Romanian UI labels', (tester) async {
    final controller = CurrencyHubLocaleController(
      preferenceStore: _MemoryLocalePreferenceStore('ro'),
    );
    addTearDown(controller.dispose);
    await _pumpApp(tester, controller);

    expect(find.text('Cursuri actuale'), findsOneWidget);
    expect(find.text('Caută valute'), findsOneWidget);
    expect(find.byKey(const Key('rate-MDL')), findsNothing);
  });

  testWidgets('renders Russian UI labels', (tester) async {
    final controller = CurrencyHubLocaleController(
      preferenceStore: _MemoryLocalePreferenceStore('ru'),
    );
    addTearDown(controller.dispose);
    await _pumpApp(tester, controller);

    expect(find.text('Текущие курсы'), findsOneWidget);
    expect(find.text('Поиск валют'), findsOneWidget);
    expect(find.byKey(const Key('rate-MDL')), findsNothing);
  });

  testWidgets('switching language updates the UI and active drawer label', (
    tester,
  ) async {
    final controller = CurrencyHubLocaleController(
      preferenceStore: _MemoryLocalePreferenceStore(),
    );
    addTearDown(controller.dispose);
    await _pumpApp(tester, controller);
    await _openDrawer(tester);
    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('language-selector')),
        matching: find.byType(PopupMenuButton<Locale>),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Română').last);
    await tester.pumpAndSettle();

    expect(find.text('Cursuri actuale'), findsWidgets);
    expect(find.text('Caută valute'), findsOneWidget);
    expect(find.text('Română'), findsOneWidget);
    expect(controller.locale, const Locale('ro'));
  });

  testWidgets('restores a saved locale on a new app instance', (tester) async {
    final store = _MemoryLocalePreferenceStore();
    final previousController = CurrencyHubLocaleController(
      preferenceStore: store,
    );
    await previousController.setLocale(const Locale('ru'));
    previousController.dispose();

    final restoredController = CurrencyHubLocaleController(
      preferenceStore: store,
    );
    addTearDown(restoredController.dispose);
    await _pumpApp(tester, restoredController);

    expect(find.text('Текущие курсы'), findsOneWidget);
    expect(restoredController.locale, const Locale('ru'));
  });

  testWidgets('falls back to English for an unsupported system locale', (
    tester,
  ) async {
    tester.binding.platformDispatcher.localeTestValue = const Locale('fr');
    addTearDown(tester.binding.platformDispatcher.clearLocaleTestValue);
    final controller = CurrencyHubLocaleController(
      preferenceStore: _MemoryLocalePreferenceStore(),
    );
    addTearDown(controller.dispose);
    await _pumpApp(tester, controller);

    expect(find.text('Current Rates'), findsOneWidget);
    expect(find.text('Search currencies'), findsOneWidget);
  });
}

Future<void> _pumpApp(
  WidgetTester tester,
  CurrencyHubLocaleController controller,
) async {
  final client = MockClient((request) async {
    if (request.url.path.endsWith('/currencies')) {
      return _json({
        'currencies': [
          {
            'code': 'USD',
            'name': 'US Dollar',
            'type': 'fiat',
            'is_supported': true,
          },
          {
            'code': 'MDL',
            'name': 'Moldovan Leu',
            'type': 'fiat',
            'is_supported': true,
          },
          {
            'code': 'BTC',
            'name': 'Bitcoin',
            'type': 'crypto',
            'is_supported': true,
          },
        ],
      });
    }
    return _json({
      'snapshot_id': 'localization-snapshot',
      'captured_at': '2026-11-07T08:00:00Z',
      'rates': [
        _rate('USD', '17.4', 'fiat'),
        _rate('MDL', '1', 'fiat'),
        _rate('BTC', '500000', 'crypto'),
      ],
    });
  });
  addTearDown(client.close);
  await tester.pumpWidget(
    CurrencyHubApp(
      apiClient: RatesApiClient(client: client),
      localeController: controller,
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _openDrawer(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Open navigation menu'));
  await tester.pumpAndSettle();
}

Map<String, dynamic> _rate(String code, String value, String type) => {
  'currency': code,
  'normalized_rate_to_mdl': value,
  'nominal_unit': 1,
  'provider_name': type == 'fiat' ? 'BNM' : 'CoinGecko',
  'provider_type': type,
  'effective_at': '2026-11-07T08:00:00Z',
  'freshness_state': 'live',
  'is_fallback': false,
  'is_stale': false,
};

http.Response _json(Map<String, dynamic> value) =>
    http.Response(jsonEncode(value), 200);

class _MemoryLocalePreferenceStore implements LocalePreferenceStore {
  _MemoryLocalePreferenceStore([this.savedLanguageCode]);

  String? savedLanguageCode;

  @override
  Future<String?> readLocale() async => savedLanguageCode;

  @override
  Future<void> saveLocale(String languageCode) async {
    savedLanguageCode = languageCode;
  }
}
