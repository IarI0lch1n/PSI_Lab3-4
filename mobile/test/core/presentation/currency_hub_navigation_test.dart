import 'dart:convert';

import 'package:currencyhub_mobile/core/api/rates_api_client.dart';
import 'package:currencyhub_mobile/core/presentation/currency_hub_navigation.dart';
import 'package:currencyhub_mobile/core/presentation/currency_hub_widgets.dart';
import 'package:currencyhub_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('drawer destinations navigate without stacking screens', (
    tester,
  ) async {
    final client = MockClient((request) async => _responseFor(request.url));
    addTearDown(client.close);
    final apiClient = RatesApiClient(client: client);
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        theme: CurrencyHubTheme.light,
        home: CurrencyHubNavigationShell(apiClient: apiClient),
      ),
    );
    await tester.pumpAndSettle();

    final l10n = AppLocalizations.of(
      tester.element(find.byType(CurrencyHubNavigationShell)),
    )!;
    expect(find.text('Current Rates'), findsOneWidget);
    await _openDrawer(tester);
    expect(find.byType(NavigationDrawerDestination), findsNWidgets(4));
    for (final destination in CurrencyHubDestination.values) {
      expect(find.text(destination.label(l10n)), findsWidgets);
      expect(find.byIcon(destination.icon), findsWidgets);
    }

    await tester.tap(find.text('All Currencies').last);
    await tester.pumpAndSettle();
    expect(find.text('Compare currencies'), findsOneWidget);
    await _openDrawer(tester);
    expect(
      tester
          .widget<NavigationDrawer>(find.byType(NavigationDrawer))
          .selectedIndex,
      CurrencyHubDestination.allCurrencies.index,
    );

    await tester.tap(find.text('Converter').last);
    await tester.pumpAndSettle();
    expect(find.text('Convert one amount'), findsOneWidget);
    await _openDrawer(tester);
    await tester.tap(find.text('Analytics').last);
    await tester.pumpAndSettle();
    expect(find.text('Historical Analytics'), findsOneWidget);
    expect(find.byType(CurrencyHubNavigationShell), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Future<void> _openDrawer(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Open navigation menu'));
  await tester.pumpAndSettle();
}

http.Response _responseFor(Uri uri) {
  if (uri.path.endsWith('/currencies')) {
    return _json({
      'currencies': [
        {'code': 'EUR', 'name': 'Euro', 'type': 'fiat', 'is_supported': true},
        {
          'code': 'USD',
          'name': 'US Dollar',
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
  if (uri.path.endsWith('/rates/latest')) {
    return _json({
      'snapshot_id': 'nav-snapshot',
      'captured_at': '2026-10-28T12:00:00Z',
      'rates': [
        _rate('EUR', '2', 'fiat'),
        _rate('USD', '4', 'fiat'),
        _rate('BTC', '8', 'crypto'),
      ],
    });
  }
  if (uri.path.endsWith('/convert')) {
    return _json({
      'source_amount': '1',
      'converted_amount': '0.25',
      'source_currency': 'EUR',
      'target_currency': 'BTC',
      'rate_value': '0.25',
      'rate_context': {
        'snapshot_id': 'nav-snapshot',
        'source_rate': _provenance('EUR', 'BNM'),
        'target_rate': _provenance('BTC', 'CoinGecko', type: 'crypto'),
      },
    });
  }
  if (uri.path.endsWith('/history')) {
    return _json(_history(uri.queryParameters['period'] ?? '7d'));
  }
  if (uri.path.endsWith('/analytics')) {
    return _json(_analytics(uri.queryParameters['period'] ?? '7d'));
  }
  return http.Response('Unexpected request', 404);
}

Map<String, dynamic> _rate(String code, String value, String type) => {
  ..._provenance(code, type == 'fiat' ? 'BNM' : 'CoinGecko', type: type),
  'normalized_rate_to_mdl': value,
  'nominal_unit': 1,
  'provider_type': type,
};

Map<String, dynamic> _provenance(
  String code,
  String provider, {
  String type = 'fiat',
}) => {
  'currency': code,
  'provider_name': provider,
  'provider_type': type,
  'effective_at': '2026-10-28T09:00:00Z',
  'freshness_state': 'live',
  'is_fallback': false,
  'is_stale': false,
};

Map<String, dynamic> _history(String period) => {
  'base_currency': 'EUR',
  'quote_currency': 'BTC',
  'period': period,
  'points': [
    {
      'date': '2026-10-28',
      'value': '0.25',
      'rate_context': {
        'source_rate': _provenance('EUR', 'BNM'),
        'target_rate': _provenance('BTC', 'CoinGecko', type: 'crypto'),
        'snapshot_id': 'nav-snapshot',
      },
    },
  ],
  'empty': false,
};

Map<String, dynamic> _analytics(String period) => {
  'base_currency': 'EUR',
  'quote_currency': 'BTC',
  'period': period,
  'points': [
    {'date': '2026-10-28', 'value': '0.25'},
  ],
  'minimum': '0.25',
  'maximum': '0.25',
  'average': '0.25',
  'absolute_change': '0',
  'percentage_change': '0',
  'trend': 'UNCHANGED',
  'provenance_summary': {
    'point_count': 1,
    'source_providers': ['BNM'],
    'target_providers': ['CoinGecko'],
    'rate_entry_freshness_counts': {'live': 2, 'fallback': 0, 'cached': 0},
    'stale_entry_count': 0,
    'fallback_entry_count': 0,
  },
  'empty': false,
};

http.Response _json(Map<String, dynamic> value) =>
    http.Response(jsonEncode(value), 200);
