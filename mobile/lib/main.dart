import 'dart:async';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'core/api/rates_api_client.dart';
import 'core/presentation/currency_hub_navigation.dart';
import 'core/presentation/currency_hub_locale_controller.dart';
import 'core/presentation/currency_hub_widgets.dart';
import 'l10n/app_localizations.dart';

void main() {
  runApp(const CurrencyHubApp());
}

class CurrencyHubApp extends StatefulWidget {
  const CurrencyHubApp({super.key, this.apiClient, this.localeController});

  final RatesApiClient? apiClient;
  final CurrencyHubLocaleController? localeController;

  @override
  State<CurrencyHubApp> createState() => _CurrencyHubAppState();
}

class _CurrencyHubAppState extends State<CurrencyHubApp> {
  late final http.Client _httpClient;
  late final RatesApiClient _apiClient;
  late final CurrencyHubLocaleController _localeController;
  late final bool _ownsLocaleController;

  @override
  void initState() {
    super.initState();
    _httpClient = http.Client();
    _apiClient = widget.apiClient ?? RatesApiClient(client: _httpClient);
    _ownsLocaleController = widget.localeController == null;
    _localeController =
        widget.localeController ?? CurrencyHubLocaleController();
    unawaited(_restoreLocale());
  }

  Future<void> _restoreLocale() async {
    try {
      await _localeController.restore();
    } on Exception catch (error, stackTrace) {
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          stack: stackTrace,
          library: 'CurrencyHub localization',
          context: ErrorDescription('while restoring the saved language'),
        ),
      );
    }
  }

  @override
  void dispose() {
    _httpClient.close();
    if (_ownsLocaleController) _localeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CurrencyHubLocaleScope(
      controller: _localeController,
      child: AnimatedBuilder(
        animation: _localeController,
        builder: (context, _) => MaterialApp(
          onGenerateTitle: (context) => AppLocalizations.of(context)!.appName,
          locale: _localeController.locale,
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          localeResolutionCallback: (locale, supportedLocales) =>
              CurrencyHubLocaleController.resolveLocale(
                locale,
                supportedLocales,
              ),
          theme: CurrencyHubTheme.light,
          home: CurrencyHubNavigationShell(apiClient: _apiClient),
        ),
      ),
    );
  }
}
