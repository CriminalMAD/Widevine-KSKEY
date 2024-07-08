import re, requests, glob, os, base64
from base64 import b64encode, b64decode
from modules.utils import get_service_module, get_cookies_module
from pywidevine.pssh import PSSH
from pywidevine.device import Device
from pywidevine.cdm import Cdm
from services.hbogo import get_license
from modules.pssh import get_pssh, get_pssh_from_mpd
from services.skyshowtime import get_user_token, get_vod_request, calculate_signature
from services.directtv import get_data
from services.netflix import download_netflix
from services import paralelo
from colorama import Fore
from modules.logging import setup_logging

logging = setup_logging()

def load_first_wvd_file(directory="."):
    wvd_files = glob.glob(os.path.join(directory, '*.wvd'))
    if wvd_files:
        return Device.load(wvd_files[0])
    else:
        logging.error("No .wvd files found in the directory.")

def get_license_keys(pssh, lic_url, service_name, content_id=None, proxy=None):
    logging.info(f"{Fore.YELLOW}Getting license keys for service: {Fore.GREEN}{service_name}")
    print(Fore.MAGENTA + "=============================================================================================================")
    logging.info(f"{Fore.YELLOW}PSSH: {Fore.RED}{pssh}")
    print(Fore.MAGENTA + "=============================================================================================================")
    logging.info(f"{Fore.YELLOW}License URL: {Fore.RED}{lic_url}")
    print(Fore.MAGENTA + "=============================================================================================================")
    logging.info(f"{Fore.YELLOW}Proxies: {Fore.RED}{proxy}")
    print(Fore.MAGENTA + "=============================================================================================================")

    if service_name == "hbogo":
        if not content_id:
            logging.error("Content ID is required for HBOGO service.")
            return False, None
        data = get_license(content_id)
        logging.debug(f"License data: {data}")
        return True, []
    
    # logging.debug(f"{Fore.GREEN}Headers: {Fore.YELLOW}{headers}{Fore.RESET}")
    # print(Fore.MAGENTA + "=============================================================================================================")
    # logging.debug(f"{Fore.GREEN}Data: {Fore.YELLOW}{data}{Fore.RESET}")
    # print(Fore.MAGENTA + "=============================================================================================================")
    # logging.debug(f"{Fore.GREEN}Params: {Fore.YELLOW}{params}{Fore.RESET}")
    # print(Fore.MAGENTA + "=============================================================================================================")
    # logging.debug(f"{Fore.GREEN}Cookies: {Fore.YELLOW}{cookies}{Fore.RESET}")

    device = load_first_wvd_file()
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
    challenge_b64 = b64encode(challenge).decode('utf-8')
    # print(challenge_b64).add()
    
    service_module = get_service_module(service_name)
    
    headers = getattr(service_module, 'get_headers', lambda: {})()
    data = getattr(service_module, 'get_data', lambda: {})()
    params = getattr(service_module, 'get_params', lambda: {})()
    cookies = getattr(service_module, 'get_cookies', lambda: {})()
    
    if not pssh:
        logging.error("No PSSH data provided or extracted.")
        return False, None
    
    if service_name == "prime":
        data['widevine2Challenge'] = challenge_b64
        response = requests.post(url=lic_url, headers=headers, params=params, cookies=cookies, data=data, proxies=proxy)
        print(response.text)
    elif service_name in ["astro", "apple", "music-amz"]:
        data['licenseChallenge'] = challenge_b64
        response = requests.post(url=lic_url, headers=headers, cookies=cookies, json=data, proxies=proxy)
    elif service_name =="tonton":
        response = requests.post(url=lic_url, headers=headers, data=challenge, proxies=proxy)
    elif service_name == "youku":
        data["licenseRequest"] = b64decode(challenge)
        response = requests.post(url=lic_url, headers=headers, data=data, proxies=proxy)
    elif service_name in ["vdocipher", "newsnow"]:
        data["licenseRequest"] = challenge_b64
        response = requests.post(url=lic_url, headers=headers, cookies=cookies, json=data, proxies=proxy)
    elif service_name in ["filmo", "viaplay", "peacock", "rakuten", "viki", "paramountplus", "crunchyroll", "hbomax"]:
        response = requests.post(url=lic_url, headers=headers, params=params, cookies=cookies, data=challenge, proxies=proxy)
    elif service_name == "unifi":
        response = requests.post(url=lic_url, headers=headers, params=params, data=challenge, proxies=proxy, verify=False)
    elif service_name == "flow":
        response = requests.post(url=lic_url, headers=headers, data=challenge, cookies=cookies, proxies=proxy)
        print(response.text)
    elif service_name == "skyshowtime":
        token_url = 'https://ovp.skyshowtime.com/auth/tokens'
        vod_url = 'https://ovp.skyshowtime.com/video/playouts/vod'
        region = cookies['activeTerritory']
        user_token = get_user_token(token_url, cookies, region)
        video_url = content_id
        vod_request = get_vod_request(vod_url, region, user_token, video_url)
        license_url = vod_request['protection']['licenceAcquisitionUrl']
        manifest_url = vod_request['asset']['endpoints'][0]['url']
        pssh = get_pssh(manifest_url)
        response = requests.post(url=license_url, headers=headers, data=challenge, proxies=proxy)
    elif service_name == "udemy":
        response = requests.post(url=lic_url, headers=headers, params=params, cookies=cookies, data=challenge, proxies=proxy)
    elif service_name == "virgintv":
        response = requests.post(url=lic_url, headers=headers, params=params, cookies=cookies, data=challenge, proxies=proxy)
    elif service_name == "directtv":
        data["licenseChallenge"] = challenge_b64
        response = requests.post(url=lic_url, headers=headers, json=data, proxies=proxy)
    elif service_name == "canal":
        data["ServiceRequest"]["InData"]["ChallengeInfo"] = challenge_b64
        response = requests.post(url=lic_url, headers=headers, json=data, proxies=proxy)
    elif service_name == "paralelo":
        data = paralelo.get_data().get('query')
        response = requests.post(url=lic_url, headers=headers, json={'query': data}, proxies=proxy)
    elif service_name == "channel5":
        response = requests.post(url=lic_url, headers=headers, params=params, data=challenge, proxies=proxy)
    else:
        response = requests.post(url=lic_url, headers=headers, params=params, cookies=cookies, data=challenge, proxies=proxy)
    
    if response.status_code != 200:
        logging.error(f"Failed to retrieve license: {response.text}")
        return False, None

    if service_name == "prime":
        license_b64 = response.json()["widevine2License"]["license"]
    elif service_name == "astro":
        license_b64 = response.json()["licenseData"][0]
    elif service_name in ["skyshowtime","tonton", "bitmovin", "unifi", "rakuten", "paramountplus", "joyn", "beinsports", "viki", "hbomax"]:
        license_b64 = b64encode(response.content).decode()
    elif service_name == "apple":
        license_b64 = response.json()['streaming-response']['streaming-keys'][0]['license']
    elif service_name == "youku":
        response_data_bytes = b64decode(response.json()["data"].encode('utf-8'))
        license_b64 = b64encode(response_data_bytes).decode()
    elif service_name in ["mubi", "dazn", "vdocipher", "newsnow", "beinsports", "viaplay", "peacock"]:
        license_b64 = b64encode(response.content).decode()
    elif service_name in ["music-amz", "crunchyroll"]:
        license_b64 = response.json()["license"]
    elif service_name == "filmo":
        license_b64 = base64.b64encode(response.content)
    elif service_name == "virgintv":
        license_b64 = response.content
    elif service_name == "directtv":
        license_b64 = response.json()['licenseData']
    elif service_name == "canal":
        license_b64 = response.json()["ServiceResponse"]["OutData"]["LicenseInfo"]
    elif service_name == "paralelo":
        license_b64 = response.json()["data"]["drm_license"]["license"]
    elif service_name == "channel5":
        license_b64 = b64encode(response.content).decode()
    else:
        logging.error(f"Service '{service_name}' is not handled.")
        return False, None

    cdm.parse_license(session_id, license_b64)
    returned_keys = []
    cached_keys = ""
    for key in cdm.get_keys(session_id):
        if key.type != "SIGNING":
            returned_keys.append(f"--key {key.kid.hex}:{key.key.hex()}")
            cached_keys += f"--key {key.kid.hex}:{key.key.hex()}\n"
    cdm.close(session_id)

    # output_file = "logs/keys.txt"
    # with open(output_file, "w") as file:
    #     file.write(cached_keys)

    # logging.info(f"Keys saved to {output_file}")
    return returned_keys