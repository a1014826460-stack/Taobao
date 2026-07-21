import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ITEM_ID = "1007839388129"
DEFAULT_SKU_ID = "6277426546603"
ADDRESS_ID = "22802236364"
APP_KEY = "12574478"
API = "mtop.taobao.pcdetail.data.adjust"
RAW_OUTPUT = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "raw"
    / "tmall"
    / "pcdetail_adjust_1007839388129.json"
)


def cookie_value(cookie, name):
    for part in cookie.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator and key == name:
            return value
    return None


def mtop_sign(token, timestamp, data):
    source = "&".join((token.split("_", 1)[0], timestamp, APP_KEY, data))
    return hashlib.md5(source.encode("utf-8")).hexdigest()


def parse_jsonp(body):
    match = re.fullmatch(r"\s*[^(]+\((.*)\)\s*", body, re.DOTALL)
    if not match:
        return json.loads(body)
    return json.loads(match.group(1))


def build_data(sku_id, timestamp):
    ex_params = {
        "addressId": ADDRESS_ID,
        "id": ITEM_ID,
        "skuId": sku_id,
        "queryParams": f"addressId={ADDRESS_ID}&id={ITEM_ID}&skuId={sku_id}",
        "domain": "https://detail.tmall.com",
        "path_name": "/item.htm",
        "pcSource": "pcTaobaoMainSSR",
        "modules": "skuClick",
        "quantity": 1,
        "uniqueId": f"{sku_id}_quantity1_{timestamp}",
        "actionType": "skuClick",
        "hidePcOtherSkuPrice": False,
    }
    return json.dumps(
        {"id": ITEM_ID, "detail_v": "3.3.2", "exParams": json.dumps(ex_params, separators=(",", ":"))},
        separators=(",", ":"),
    )


def request_adjust(cookie, sku_id):
    token = cookie_value(cookie, "_m_h5_tk")
    if not token:
        raise RuntimeError("TMALL_COOKIE does not contain _m_h5_tk")

    timestamp = str(int(time.time() * 1000))
    data = build_data(sku_id, timestamp)
    callback = "mtopjsonppcdetailskupanel1"
    params = {
        "jsv": "2.7.5",
        "appKey": APP_KEY,
        "t": timestamp,
        "sign": mtop_sign(token, timestamp, data),
        "_bx-login": "new",
        "api": API,
        "v": "1.0",
        "isSec": "0",
        "ecode": "0",
        "timeout": "5000",
        "jsonpIncPrefix": "pcdetailskupanel",
        "valueType": "string",
        "ttid": "2022@taobao_litepc_9.17.0",
        "AntiFlood": "true",
        "AntiCreep": "true",
        "type": "jsonp",
        "dataType": "jsonp",
        "callback": callback,
        "data": data,
    }
    url = "https://h5api.m.tmall.com/h5/mtop.taobao.pcdetail.data.adjust/1.0/?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie,
            "Referer": f"https://detail.tmall.com/item.htm?id={ITEM_ID}&skuId={sku_id}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, parse_jsonp(response.read().decode("utf-8", "replace")), params


def main():
    cookie = os.environ["TMALL_COOKIE"]
    sku_id = os.getenv("TMALL_SKU_ID", DEFAULT_SKU_ID)
    status, payload, params = request_adjust(cookie, sku_id)
    sku = payload.get("data", {}).get("skuCore", {}).get("sku2info", {}).get(sku_id, {})
    result = {
        "http_status": status,
        "ret": payload.get("ret"),
        "request": {key: params[key] for key in ("t", "sign", "ttid", "data")},
        "sku": {
            "sku_id": sku_id,
            "price": sku.get("price"),
            "sub_price": sku.get("subPrice"),
            "quantity": sku.get("quantity"),
            "quantity_text": sku.get("quantityText"),
            "logistics_time": sku.get("logisticsTime"),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    output_path = Path(os.getenv("TMALL_OUTPUT_PATH", RAW_OUTPUT))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
