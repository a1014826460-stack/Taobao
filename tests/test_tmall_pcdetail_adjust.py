import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).parents[1] / "src" / "tmall" / "direct" / "pcdetail_adjust.py"
    spec = importlib.util.spec_from_file_location("pcdetail_adjust", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mtop_sign_uses_token_prefix_and_exact_data():
    module = load_module()
    assert module.mtop_sign("token_123", "1700000000000", '{"id":"1"}') == "6c24d0cf9bdb0c50b9c6d4f7934994de"


def test_parse_jsonp_and_json_return_payloads():
    module = load_module()
    assert module.parse_jsonp('cb({"ret":["SUCCESS"]})') == {"ret": ["SUCCESS"]}
    assert module.parse_jsonp('{"ret":["SUCCESS"]}') == {"ret": ["SUCCESS"]}


def test_build_data_contains_sku_click_context():
    module = load_module()
    data = module.build_data("6277426546603", "1700000000000")
    outer = json.loads(data)
    inner = json.loads(outer["exParams"])
    assert outer["id"] == "1007839388129"
    assert outer["detail_v"] == "3.3.2"
    assert inner["skuId"] == "6277426546603"
    assert inner["uniqueId"] == "6277426546603_quantity1_1700000000000"
    assert inner["modules"] == "skuClick"
