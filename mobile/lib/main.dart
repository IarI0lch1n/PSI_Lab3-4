import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'core/api/rates_api_client.dart';
import 'features/converter/presentation/converter_screen.dart';
import 'features/rates/presentation/current_rates_screen.dart';
import 'features/rates/presentation/all_currencies_screen.dart';

void main() {
  runApp(const CurrencyHubApp());
}

class CurrencyHubApp extends StatefulWidget {
  const CurrencyHubApp({super.key});

  @override
  State<CurrencyHubApp> createState() => _CurrencyHubAppState();
}

class _CurrencyHubAppState extends State<CurrencyHubApp> {
  late final http.Client _httpClient;
  late final RatesApiClient _apiClient;

  @override
  void initState() {
    super.initState();
    _httpClient = http.Client();
    _apiClient = RatesApiClient(client: _httpClient);
  }

  @override
  void dispose() {
    _httpClient.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CurrencyHub',
      home: CurrentRatesScreen(apiClient: _apiClient),
      routes: {
        '/converter': (_) => ConverterScreen(apiClient: _apiClient),
        '/all-currencies': (_) => AllCurrenciesScreen(apiClient: _apiClient),
      },
    );
  }
}
