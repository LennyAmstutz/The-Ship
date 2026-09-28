import datetime
from urllib.parse import urlsplit

import requests

from Actions import s3_sigv4
from config import S3_ACCESS_KEY, S3_HOST, S3_PORT, S3_REGION, S3_SECRET_KEY

# Mini-S3-Client mit AWS Signature V4 (ersetzt boto3/minio, die auf dem Schiff fehlen).
# Funktioniert mit unserem s3_server.py und mit einem echten MinIO.

ENDPOINT = f"http://{S3_HOST}:{S3_PORT}"


def _request(method, path, body=b"", timeout=10):
    """Schickt eine unterschriebene Anfrage. path ist schon URL-codiert, z.B. /analyzer-gamma/data.hex"""
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    scope = f"{now:%Y%m%d}/{S3_REGION}/s3/aws4_request"
    url = urlsplit(ENDPOINT + path)
    headers = {
        "host": url.netloc,
        "x-amz-content-sha256": s3_sigv4.sha256_hex(body),
        "x-amz-date": amz_date,
    }
    signed_headers = sorted(headers)
    signature = s3_sigv4.signature(S3_SECRET_KEY, method, url.path, [], headers, signed_headers,
                                   headers["x-amz-content-sha256"], amz_date, scope)
    headers["authorization"] = (f"{s3_sigv4.ALGORITHM} Credential={S3_ACCESS_KEY}/{scope}, "
                                f"SignedHeaders={';'.join(signed_headers)}, Signature={signature}")
    return requests.request(method, ENDPOINT + path, data=body, headers=headers, timeout=timeout)


def _path(bucket, key=""):
    return f"/{s3_sigv4.uri_encode(bucket)}" + (f"/{s3_sigv4.uri_encode(key, safe='-_.~/')}" if key else "")


def ensure_bucket(bucket):
    """Legt den Bucket an, falls es ihn noch nicht gibt."""
    if _request("HEAD", _path(bucket)).status_code == 200:
        return
    response = _request("PUT", _path(bucket))
    if response.status_code not in (200, 409):          # 409 = gibt es schon
        raise RuntimeError(f"Bucket {bucket} anlegen: {response.status_code} {response.text.strip()}")


def put_object(bucket, key, data):
    if isinstance(data, str):
        data = data.encode()
    response = _request("PUT", _path(bucket, key), data)
    if response.status_code != 200:
        raise RuntimeError(f"PUT {bucket}/{key}: {response.status_code} {response.text.strip()}")


def get_object(bucket, key):
    response = _request("GET", _path(bucket, key))
    if response.status_code != 200:
        raise RuntimeError(f"GET {bucket}/{key}: {response.status_code} {response.text.strip()}")
    return response.content
