import requests
import sys


import requests


headers = {
    "accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://iqoo.tmall.com/search.htm?orderType=defaultSort&viewType=grid&keyword=&lowPrice=&highPrice=",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Microsoft Edge\";v=\"150\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "x-requested-with": "XMLHttpRequest"
}
cookies = {
    "cna": "kYIWIWtjOUcCAXtYEfTYtDcM",
    "lid": "tb619838021",
    "hng": "GLOBAL%7Czh-CN%7CUSD%7C999",
    "wk_cookie2": "1a26e39dcba428927607f7ff89db7565",
    "wk_unb": "UNaGuKCocoh3MQ%3D%3D",
    "lgc": "tb619838021",
    "login": "true",
    "cookie2": "2712ebf0cbff6c5fa4119b6b41dba8f6",
    "cancelledSubSites": "empty",
    "sn": "",
    "_tb_token_": "e543ee76ee73e",
    "dnk": "tb619838021",
    "tracknick": "tb619838021",
    "t": "a3d77fd67934f1385f8909bf7aa3ac61",
    "xlly_s": "1",
    "_l_g_": "Ug%3D%3D",
    "cookie1": "UNcMJIPeSeK%2BAo39ra9nHfNHPekflIwqHl1FhARpE9s%3D",
    "sg": "181",
    "unb": "3610788698",
    "cookie17": "UNaGuKCocoh3MQ%3D%3D",
    "_nk_": "tb619838021",
    "csg": "27f9f366",
    "uc1": "cookie16",
    "uc3": "vt3",
    "uc4": "id4",
    "sgcookie": "E100dryVCDvSt%2F0A%2Fq6RQtK0WhWGFbGNVydoVEZW%2BcDa06d0%2BycHrF2KT8ePaU6cQzSA%2B%2FoXfys4oCJMlerYuhHMmhPsmkpi255eYA%2FiuniVrmXab5IcA%2FUBN6HcX0bOiBDh",
    "mtop_partitioned_detect": "1",
    "_m_h5_tk": "bde5634f2d39544d8bbffd85364465f3_1784448658330",
    "_m_h5_tk_enc": "ce33ccae4321dc34639c36b8fb6acf3a",
    "bxuab": "0",
    "havana_sdkSilent": "1784470259358",
    "havana_lgc_exp": "1815545459358",
    "pnm_cku822": "",
    "isg": "BKWlnWdNI_h_a0Vn-dJw8e0ptGHf4ll0mEn4BKeFdFzfvsEwbjOSRIgdTCLIvnEs",
    "tfstk": "hcqyyr4oyWwONZi8O8i_Y27jL0e-S7xBADG5oSl0aYGSVJD3YWNmA2f-VkPqADf_d0L-LQHsKQjIrHAck9myL1s1f8QoeDw0dBFQ0xDZIDDoZb0c3vDKtD0otiXqKvOotbV3ntkKi3xHxYcmmvMwtXVnxtymMvmntW0l3-cxKDchP_xUlADxub_RIHMVdYurTHG0lk6I34lgEu-y4ODzp80Qrh7IsPhS5SVcc3oUnvPZQ7RcgD242lu0qsKEkHJ26H-Q1gTQmMe8lSz1qIqhion0dWS2s1BuR-wUSE_8VuVuyc2wBGfOduqY0RIvyu13u-2n-eCRMGV7r8EXzaCCjRi_i5Dq3ZDHupUGk3AvJe38kxl1eTLpJ4Dx3f6V3eLKycHq1TBR."
}
url = "https://iqoo.tmall.com/i/asynSearch.htm"
params = {
    "_ksTS": "1784441910919_90",
    "callback": "jsonp91",
    "mid": "w-14962063618-0",
    "wid": "14962063618",
    "path": "/search.htm",
    "search": "y",
    "orderType": "defaultSort",
    "viewType": "grid",
    "keyword": "null",
    "lowPrice": "null",
    "highPrice": "null"
}


def build_session() -> requests.Session:
    """Create a requests session that bypasses system proxy settings.

    On this machine Windows has a system HTTPS proxy configured at
    127.0.0.1:9000. requests reads that proxy by default, and the proxy's
    locally generated certificate is not trusted by certifi, causing
    CERTIFICATE_VERIFY_FAILED. Bypassing environment proxy settings keeps TLS
    verification enabled while connecting directly to detail.tmall.com.
    """
    session = requests.Session()
    session.trust_env = False
    return session


def fetch_item_page(
    item_url: str = url,
    request_headers: dict | None = None,
    request_cookies: dict | None = None,
    request_params: dict | None = None,
    timeout: int = 30,
) -> requests.Response:
    session = build_session()
    response = session.get(
        item_url,
        headers=request_headers or headers,
        cookies=request_cookies or cookies,
        params=request_params or params,
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def configure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    configure_stdout_utf8()
    response = fetch_item_page()
    print(response.text)
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
