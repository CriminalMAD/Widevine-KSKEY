import hmac, hashlib, sys, time, base64, requests, json
from modules.logging import setup_logging
from urllib.parse import urlparse

logging = setup_logging()

def get_headers():
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/octet-stream',
    'DNT': '1',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'X-Forwarded-For': '89.45.7.28'
    # Requests doesn't support trailers
    # 'TE': 'trailers',
}
    return headers

def get_params():
    params = {}
    return params

def get_cookies():
    cookies = {}
    return cookies

def get_data():
    data = ""
    return data

def calculate_signature(method, url, headers, payload, timestamp=None):
    app_id = 'SKYSHOWTIME-ANDROID-v1'
    signature_key = bytearray('jfj9qGg6aDHaBbFpH6wNEvN6cHuHtZVppHRvBgZs', 'utf-8')
    sig_version = '1.0'

    if not timestamp:
        timestamp = int(time.time())

    if url.startswith('http'):
        parsed_url = urlparse(url)
        path = parsed_url.path
    else:
        path = url

    text_headers = ''
    for key in sorted(headers.keys()):
        if key.lower().startswith('x-skyott'):
            text_headers += key + ': ' + headers[key] + '\n'
    headers_md5 = hashlib.md5(text_headers.encode()).hexdigest()

    if sys.version_info[0] > 2 and isinstance(payload, str):
        payload = payload.encode('utf-8')
    payload_md5 = hashlib.md5(payload).hexdigest()

    to_hash = ('{method}\n{path}\n{response_code}\n{app_id}\n{version}\n{headers_md5}\n'
               '{timestamp}\n{payload_md5}\n').format(method=method, path=path,
                                                      response_code='', app_id=app_id, version=sig_version,
                                                      headers_md5=headers_md5, timestamp=timestamp, payload_md5=payload_md5)

    hashed = hmac.new(signature_key, to_hash.encode('utf8'), hashlib.sha1).digest()
    signature = base64.b64encode(hashed).decode('utf8')
    return 'SkyOTT client="{}",signature="{}",timestamp="{}",version="{}"'.format(app_id, signature, timestamp, sig_version)

def get_user_token(token_url, cookies, region):
    headers = {
        'accept': 'application/vnd.tokens.v1+json',
        'content-type': 'application/vnd.tokens.v1+json',
    }
    post_data = {
        "auth": {
            "authScheme": 'MESSO',
            "authIssuer": 'NOWTV',
            "provider": 'SKYSHOWTIME',
            "providerTerritory": region,
            "proposition": 'SKYSHOWTIME',
        },
        "device": {
            "type": 'MOBILE',
            "platform": 'ANDROID',
            "id": 'Z-sKxKApSe7c3dAMGAYtVU8NmWKDcWrCKobKpnVTLqc',
            "drmDeviceId": 'UNKNOWN'
        }
    }
    post_data = json.dumps(post_data)
    headers['x-sky-signature'] = calculate_signature('POST', token_url, headers, post_data)
    response = requests.post(token_url, cookies=cookies, headers=headers, data=post_data)
    response.raise_for_status()
    return response.json()['userToken']

def get_vod_request(vod_url, region, user_token, video_url):
    content_id = video_url.split("/")[6]
    provider_variant_id = video_url.split("/")[7][:36]

    post_data = {
        "providerVariantId": provider_variant_id,
        "device": {
            "capabilities": [
                {"transport": "DASH", "protection": "NONE", "vcodec": "H265", "acodec": "AAC", "container": "ISOBMFF"},
                {"transport": "DASH", "protection": "WIDEVINE", "vcodec": "H265", "acodec": "AAC", "container": "ISOBMFF"},
                {"transport": "DASH", "protection": "NONE", "vcodec": "H264", "acodec": "AAC", "container": "ISOBMFF"},
                {"transport": "DASH", "protection": "WIDEVINE", "vcodec": "H264", "acodec": "AAC", "container": "ISOBMFF"}
            ],
            "model": "SM-N986B",
            "maxVideoFormat": "HD",
            "hdcpEnabled": 'false',
            "supportedColourSpaces": ["SDR"]
        },
        "client": {"thirdParties": ["COMSCORE", "CONVIVA", "FREEWHEEL"]},
        "personaParentalControlRating": 9
    }
    post_data = json.dumps(post_data)
    headers = {
        'accept': 'application/vnd.playvod.v1+json',
        'content-type': 'application/vnd.playvod.v1+json',
        'x-skyott-activeterritory': region,
        'x-skyott-agent': 'skyshowtime.mobile.android',
        'x-skyott-country': region,
        'x-skyott-device': 'MOBILE',
        'x-skyott-platform': 'ANDROID',
        'x-skyott-proposition': 'NBCUOTT',
        'x-skyott-provider': 'SKYSHOWTIME',
        'x-skyott-territory': region,
        'x-skyott-usertoken': user_token,
    }
    headers['x-sky-signature'] = calculate_signature('POST', vod_url, headers, post_data)
    response = requests.post(vod_url, headers=headers, data=post_data)
    response.raise_for_status()
    logging.info(response.json()['asset']['endpoints'][0]['url'])
    return response.json()