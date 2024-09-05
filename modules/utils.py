import shutil, sys, os
from pathlib import Path
from typing import Optional
import pyfiglet
from colorama import Fore, Style
import importlib
from modules.logging import setup_logging
import requests
import random
import os
import uuid, secrets
from colorama import Fore
from http.cookiejar import MozillaCookieJar

logging = setup_logging()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_headers(header_list):
    """
    Convert a list of header strings into a dictionary.

    Args:
        header_list (list): List of headers in the format "Key: Value".

    Returns:
        dict: Dictionary of headers.
    """
    headers = {}
    if header_list:
        for header in header_list:
            if ':' in header:
                try:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()
                except ValueError as e:
                    logging.warning(f"Failed to process header: {header} due to {str(e)}.")
            else:
                pass
    return headers

def colored_input(prompt, color):
    print(color + prompt + Style.RESET_ALL, end='')
    return input()

def get_binary_path(*names: str) -> Optional[Path]:
    """Get the path of the first found binary name."""
    for name in names:
        path = shutil.which(name)
        if path:
            return Path(path)
    return None

def print_title(title_text, proxy=None):
    title = pyfiglet.figlet_format(title_text, font='slant')
    if proxy:
        print(Fore.YELLOW + f"{title}Running with proxy settings: {proxy}" + Style.RESET_ALL)
    else:
        print(Fore.CYAN + f"{title}Running " + Style.RESET_ALL)

def print_license_keys(keys):
    for key in keys:
        logging.info(key)
    print(Fore.MAGENTA + "=============================================================================================================")
    logging.success("All Done...")

def get_service_module(service_name):
    try:
        return importlib.import_module(f'services.{service_name}')
    except ImportError:
        logging.error(f"No module named '{service_name}' found in 'services' package")
        sys.exit(1)
        
def get_cookies_module(service_name):
    try:
        return importlib.import_module(f'cookies.{service_name}')
    except ImportError:
        logging.error(f"No module named '{service_name}' found in 'cookies' package")
        sys.exit(1)

metadata_endpoint = 'https://www.netflix.com/nq/website/memberapi/{}/metadata'
default_file_name = "$ftitle$.$year$.$fseason$$fepisode$.NF.WEBDL.$quality$p.$audios$.$acodec$.$vcodec$-dvx.mkv"

def random_hex(length: int) -> str:
	return "".join(random.choice("0123456789ABCDEF") for _ in range(length))

def pretty_size(size: int) -> str:
    return f"{size/float(1<<20):,.0f}MiB"

manifest_esn = f"NFCDCH-02-{random_hex(30)}" # NFCDCH-02-L8Z2W1GRV6VKDKV3FP2EL9M6QVQYUT

def get_android_esn(quality: int) -> str:
    """Generate an ESN based on video quality."""
    # Ensure quality is an integer
    try:
        quality = int(quality)
    except ValueError:
        raise ValueError("Quality should be an integer")

    if quality >= 2160:
        device_id = 2  # 4K quality
    elif quality >= 1080:
        device_id = 1  # Full HD quality
    elif quality >= 720:
        device_id = 3  # HD quality
    elif quality >= 540:
        device_id = 4  # qHD quality
    else:
        device_id = 0  # Standard quality
    
    # Generate the ESN with a random 30-character hex string
    esn = f"NFANDROID{device_id}-PRV-P-SAMSUSM-G950F-7169-{random_hex(30)}"
    
    return esn


def shakti_headers(build_id):
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "es,ca;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Host": "www.netflix.com",
        "Pragma": "no-cache",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "X-Netflix.browserName": "Firefox",
        "X-Netflix.browserVersion": "123",
        "X-Netflix.clientType": "akira",
        "X-Netflix.Client.Request.Name": "ui/falcorUnclassified",
        "X-Netflix.esnPrefix": "NFCDFF-02-",
        "X-Netflix.osFullName": "Windows 10",
        "x-netflix.nq.stack": "prod",
        "X-Netflix.osName": "Windows",
        "X-Netflix.osVersion": "10.0",
        "X-Netflix.playerThroughput": "58194",
        "X-Netflix.uiVersion": str(build_id),
        "x-netflix.request.client.user.guid": str(uuid.uuid4()).replace("-", ""),
        "X-Forwarded-For": "194.36.178.234"
    }

def build_headers():
    return {
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en,en-US;q=0.9",
        "X-Forwarded-For": "194.36.178.234"
    }

def get_build_id() -> str:
    r = requests.get("https://www.netflix.com/buildIdentifier")
    print(r.text)
    if r.status_code != 200:
        print(f"{Fore.YELLOW}[Widevine-KSKEY] - {Fore.RED}Netflix didn't return 200!")
        raise Exception("Netflix didn't return 200")
    return r.json()["BUILD_IDENTIFIER"]

def read_data(cookies_file):
    if not os.path.exists(cookies_file):
        print(f"{Fore.YELLOW}[Widevine-KSKEY] - {Fore.RED}Missing cookie file. ({cookies_file})")
        raise Exception(f"Missing cookie file. ({cookies_file})")
    cj = MozillaCookieJar(cookies_file)
    cj.load()
    cookies = {
        cookie.name: cookie.value
        for cookie in cj
    }
    cookies["build_id"] = get_build_id()
    if "NetflixId" not in cookies:
        print(f"{Fore.YELLOW}[Widevine-KSKEY] - {Fore.RED}Invalid cookies. (Missing NetflixId)")
        raise Exception("Invalid cookies. (Missing NetflixId)")
    return cookies

lang_codes = {
    "fil": ["Filipino", "fil"],
    "cy": ["Welsh", "cym"],
    "cs": ["Czech", "ces"],
    "de": ["German", "ger"],
    "en": ["English", "eng"],
    "es": ["Spanish", "spa"],
    "bg": ["Bulgarian", "bul"],
    "ar-EG": ["Egyptian Arabic", "ara"],
    "ar-SY": ["Syrian Arabic", "ara"],
    "en-GB": ["Britain English", "eng"],
    "es-ES": ["European Spanish", "spa"],
    "fr-CA": ["Canadian French", "fra"],
    "fr": ["French", "fra"],
    "hi": ["Hindi", "hin"],
    "hu": ["Hungarian", "hun"],
    "id": ["Indonesian", "ind"], 
    "it": ["Italian", "ita"],
    "pl": ["Polish", "pol"],
    "pt-BR": ["Brazilian Portuguese", "por"],
    "ru": ["Russian", "rus"],
    "ta": ["Tamil", "tam"],
    "te": ["Telugu", "tel"],
    "th": ["Thai", "tha"],
    "tr": ["Turkish", "tur"],
    "uk": ["Ukrainian", "ukr"],
    "ar": ["Arabic", "ara"],
    "da": ["Danish", "dan"],
    "el": ["Greek", "ell"],
    "fi": ["Finnish", "fin"],
    "he": ["Hebrew", "heb"],
    "hi-Latn": ["Hindi", "hin"],
    "hr": ["Croatian", "hrv"],
    "ja": ["Japanese", "jpn"],
    "ko": ["Korean", "kor"],
    "ms": ["Malay", "msa"],
    "nb": ["Norwegian", "nob"],
    "nl": ["Dutch", "nld"],
    "pt": ["Portuguese", "por"],
    "ro": ["Romanian", "ron"],
    "sv": ["Swedish", "swe"],
    "vi": ["Vietnamese", "vie"],
    "zh": ["Chinese", "zho"],
    "zh-Hans": ["Simplified Chinese", "zho"],
    "zh-Hant": ["Traditional Chinese", "zho"]
}

supported_video_profiles = {
    "high": [
        "playready-h264hpl{}-dash",
        "playready-h264hpl30-dash",
        "playready-h264hpl31-dash",
        "playready-h264hpl40-dash",
        "h264hpl30-dash-playready-live",
        "h264hpl31-dash-playready-live",
        "h264hpl40-dash-playready-live"
    ],
    "main": [
        "playready-h264mpl{}-dash",
        "playready-h264mpl30-dash",
        "playready-h264mpl31-dash",
        "playready-h264mpl40-dash"
    ],
    "baseline": [
        "playready-h264bpl{}-dash"
    ],
    "hevc": [
        "hevc-main10-L{}-dash-cenc",
        "hevc-main10-L{}-dash-cenc-prk",
        "av1-main-L30-dash-cbcs-prk",
        "av1-main-L31-dash-cbcs-prk",
        "av1-main-L40-dash-cbcs-prk",
        "av1-main-L41-dash-cbcs-prk"
    ],
    "hdr": [
        "hevc-hdr-main10-L{}-dash-cenc",
        "hevc-hdr-main10-L{}-dash-cenc-prk"
    ],
    "audio": [
        "heaac-2-dash",
        "heaac-2hq-dash",
        "xheaac-dash"
    ],
    "video": [
        "vp9-profile0-L30-dash-cenc",
        "vp9-profile0-L31-dash-cenc",
        "vp9-profile0-L40-dash-cenc"
    ],
    "subtitles": [
        "imsc1.1",
        "dfxp-ls-sdh",
        "simplesdh"
    ],
    "other": [
        "nflx-cmisc",
        "BIF240",
        "BIF320"
    ]
}

supported_audio_profiles = {
    "aac": [
        "heaac-5.1-dash",
        "heaac-5.1hq-dash",
        "heaac-2-dash",
        "heaac-2hq-dash",
    ],
    "ac3": [
        "dd-5.1-dash",
        "dd-5.1-elem"
    ],
    "eac3": [
        "ddplus-5.1-dash",
        "ddplus-5.1hq-dash",
        "ddplus-2-dash"
    ],
    "dts": [
        "ddplus-atmos-dash"
    ]
}

def get_profiles(video_profile: str, audio_profile: str, quality: int):
    profiles = ["webvtt-lssdh-ios8"]
    
    # Retrieve video profiles based on the input
    video_profile_list = supported_video_profiles.get(video_profile.lower(), [])
    
    # Add video profiles based on quality
    if quality >= 2160:
        profiles += [x.format(51) for x in video_profile_list]
        profiles += [x.format(50) for x in video_profile_list]
    if quality >= 1080:
        if video_profile.lower() in ["hevc", "hdr"]:
            profiles += [x.format(41) for x in video_profile_list]
        profiles += [x.format(40) for x in video_profile_list]
    if quality >= 720:
        profiles += [x.format(31) for x in video_profile_list]
    if quality >= 480:
        profiles += [x.format(30) for x in video_profile_list]
        if video_profile.lower() not in ["hevc", "hdr"]:
            profiles += [x.format(22) for x in video_profile_list]
    
    # Add audio profiles based on the input
    audio_profiles = supported_audio_profiles.get(audio_profile.lower(), [])
    profiles += audio_profiles
    
    return profiles