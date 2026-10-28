import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/rate_models.dart';

class RatesApiClient {
  RatesApiClient({required this.client, String baseUrl = defaultBaseUrl})
    : _baseUrl = baseUrl.replaceFirst(RegExp(r'/+$'), '');

  static const defaultBaseUrl = 'http://10.0.2.2:8000/api/v1';

  final http.Client client;
  final String _baseUrl;

  Future<CurrenciesResponse> getCurrencies() async {
    final json = await _getJson('currencies');
    return CurrenciesResponse.fromJson(json);
  }

  Future<RateSnapshot> getLatestRates() async {
    final json = await _getJson('rates/latest');
    return RateSnapshot.fromJson(json);
  }

  Future<Map<String, dynamic>> _getJson(String endpoint) async {
    final uri = Uri.parse('$_baseUrl/$endpoint');
    final response = await client.get(uri);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw RatesApiException(uri: uri, statusCode: response.statusCode);
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw const FormatException(
      'Expected the API response to be a JSON object.',
    );
  }
}

class RatesApiException implements Exception {
  const RatesApiException({required this.uri, required this.statusCode});

  final Uri uri;
  final int statusCode;

  @override
  String toString() => 'RatesApiException: GET $uri returned HTTP $statusCode.';
}
