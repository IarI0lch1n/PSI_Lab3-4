import 'package:flutter/material.dart';

import '../api/rates_api_client.dart';
import '../../features/analytics/presentation/analytics_screen.dart';
import '../../features/converter/presentation/converter_screen.dart';
import '../../features/rates/presentation/all_currencies_screen.dart';
import '../../features/rates/presentation/current_rates_screen.dart';
import 'currency_hub_widgets.dart';

class CurrencyHubNavigationShell extends StatefulWidget {
  const CurrencyHubNavigationShell({required this.apiClient, super.key});

  final RatesApiClient apiClient;

  @override
  State<CurrencyHubNavigationShell> createState() =>
      _CurrencyHubNavigationShellState();
}

class _CurrencyHubNavigationShellState
    extends State<CurrencyHubNavigationShell> {
  CurrencyHubDestination _destination = CurrencyHubDestination.currentRates;

  void _navigate(CurrencyHubDestination destination) {
    if (destination == _destination) return;
    setState(() => _destination = destination);
  }

  @override
  Widget build(BuildContext context) {
    final onNavigate = _navigate;
    return switch (_destination) {
      CurrencyHubDestination.currentRates => CurrentRatesScreen(
        apiClient: widget.apiClient,
        onNavigate: onNavigate,
      ),
      CurrencyHubDestination.allCurrencies => AllCurrenciesScreen(
        apiClient: widget.apiClient,
        onNavigate: onNavigate,
      ),
      CurrencyHubDestination.converter => ConverterScreen(
        apiClient: widget.apiClient,
        onNavigate: onNavigate,
      ),
      CurrencyHubDestination.analytics => AnalyticsScreen(
        apiClient: widget.apiClient,
        onNavigate: onNavigate,
      ),
    };
  }
}
