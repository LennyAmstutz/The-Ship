import hashlib
import hmac
from urllib.parse import quote

# AWS Signature Version 4 - so unterschreiben S3-Clients (minio, boto3, aws cli) ihre Anfragen.
# Wird vom S3-Server (pruefen) und vom S3-Client (unterschreiben) in Mission 9 benutzt.
#
#   Authorization: AWS4-HMAC-SHA256 Credential=<access_key>/<datum>/<region>/s3/aws4_request,
#                  SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=<hex>
#
# Die Signatur ist ein HMAC ueber die "kanonische" Anfrage (Methode, Pfad, Query, Header, Body-Hash).
# Der Schluessel dafuer wird aus dem secret_key, dem Datum, der Region und dem Dienst abgeleitet.

ALGORITHM = "AWS4-HMAC-SHA256"
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def uri_encode(text, safe="-_.~"):
    """RFC 3986: alles ausser A-Z a-z 0-9 - _ . ~ wird prozent-codiert."""
    return quote(text, safe=safe)


def canonical_query(pairs):
    """pairs = [(key, value), ...] (schon decodiert) -> sortiert und codiert wie AWS es will."""
    encoded = sorted((uri_encode(k), uri_encode(v)) for k, v in pairs)
    return "&".join(f"{k}={v}" for k, v in encoded)


def signing_key(secret_key, date, region, service="s3"):
    key = hmac.new(f"AWS4{secret_key}".encode(), date.encode(), hashlib.sha256).digest()
    for part in (region, service, "aws4_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    return key


def signature(secret_key, method, path, query_pairs, headers, signed_headers, payload_hash, amz_date, scope):
    """headers: dict mit kleingeschriebenen Namen. scope: <datum>/<region>/s3/aws4_request."""
    canonical_headers = "".join(f"{name}:{' '.join(str(headers.get(name, '')).split())}\n"
                                for name in signed_headers)
    canonical_request = "\n".join([
        method,
        path,
        canonical_query(query_pairs),
        canonical_headers,
        ";".join(signed_headers),
        payload_hash,
    ])
    string_to_sign = "\n".join([ALGORITHM, amz_date, scope, sha256_hex(canonical_request.encode())])
    date, region, service, _ = scope.split("/")
    key = signing_key(secret_key, date, region, service)
    return hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()


def parse_authorization(value):
    """'AWS4-HMAC-SHA256 Credential=a/b/c/s3/aws4_request, SignedHeaders=x;y, Signature=z' -> dict."""
    if not value or not value.startswith(ALGORITHM + " "):
        raise ValueError("kein AWS4-HMAC-SHA256 Authorization-Header")
    parts = {}
    for item in value[len(ALGORITHM):].split(","):
        key, _, val = item.strip().partition("=")
        parts[key] = val
    access_key, _, scope = parts["Credential"].partition("/")
    return {
        "access_key": access_key,
        "scope": scope,
        "signed_headers": parts["SignedHeaders"].split(";"),
        "signature": parts["Signature"],
    }
