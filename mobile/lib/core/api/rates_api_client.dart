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

  Future<ConversionResponse> convert(ConversionRequest request) async {
    final json = await _postJson('convert', request.toJson());
    return ConversionResponse.fromJson(json);
  }

  Future<Map<String, dynamic>> _getJson(String endpoint) async {
    final uri = Uri.parse('$_baseUrl/$endpoint');
    final response = await client.get(uri);
    return _decodeJsonResponse(uri, response, method: 'GET');
  }

  Future<Map<String, dynamic>> _postJson(
    String endpoint,
    Map<String, String> body,
  ) async {
    final uri = Uri.parse('$_baseUrl/$endpoint');
    final response = await client.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decodeJsonResponse(uri, response, method: 'POST');
  }

  Map<String, dynamic> _decodeJsonResponse(
    Uri uri,
    http.Response response, {
    required String method,
  }) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final errorDetails = _readErrorDetails(response.body);
      throw RatesApiException(
        uri: uri,
        statusCode: response.statusCode,
        method: method,
        errorCode: errorDetails?.$1,
        safeMessage: errorDetails?.$2,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw const FormatException(
      'Expected the API response to be a JSON object.',
    );
  }

  (String, String)? _readErrorDetails(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        return null;
      }
      final error = decoded['error'];
      if (error is! Map<String, dynamic>) {
        return null;
      }
      final code = error['code'];
      final message = error['message'];
      if (code is String && message is String && code.isNotEmpty) {
        return (code, message);
      }
    } on FormatException {
      return null;
    }
    return null;
  }
}

class RatesApiException implements Exception {
  const RatesApiException({
    required this.uri,
    required this.statusCode,
    this.method = 'GET',
    this.errorCode,
    this.safeMessage,
  });

  final Uri uri;
  final int statusCode;
  final String method;
  final String? errorCode;
  final String? safeMessage;

  @override
  String toString() =>
      'RatesApiException: $method $uri returned HTTP $statusCode.';
}
