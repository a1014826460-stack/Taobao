from src.jd.services.item_service import run_jd_item
from src.jd.services.ware_business_service import run_jd_ware_business
from src.taobao.services.item_service import run_taobao_item
from src.taobao.services.shop_service import run_taobao_shop
from src.tmall.services.sku_adjust_service import run as tmall_sku_adjust

REGISTRY = {
    "taobao.item": run_taobao_item,
    "taobao.shop": run_taobao_shop,
    "tmall.sku-adjust": tmall_sku_adjust,
    "jd.item": run_jd_item,
    "jd.ware-business": run_jd_ware_business,
}
