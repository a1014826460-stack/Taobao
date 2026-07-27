export type CrawlerId = "taobao.item" | "taobao.shop" | "tmall.sku-adjust" | "jd.item" | "jd.ware-business";

export type CrawlerDefinition = {
  id: CrawlerId;
  platform: "taobao" | "tmall" | "jd";
  icon: string;
  credentialRequired: boolean;
  zh: { name: string; description: string; inputHint: string };
  en: { name: string; description: string; inputHint: string };
  example: Record<string, unknown>;
};

export const crawlerCatalog: CrawlerDefinition[] = [
  {
    id: "taobao.item", platform: "taobao", icon: "淘", credentialRequired: false,
    zh: { name: "淘宝商品详情", description: "通过已配置的数据网关查询单个淘宝商品。", inputHint: "输入商品 ID，例如 652874751412" },
    en: { name: "Taobao item details", description: "Fetch one Taobao item through the configured data gateway.", inputHint: "Enter an item ID" },
    example: { item_id: "652874751412" },
  },
  {
    id: "taobao.shop", platform: "taobao", icon: "淘", credentialRequired: false,
    zh: { name: "淘宝店铺商品", description: "按页读取淘宝店铺的商品列表。", inputHint: "店铺 ID、卖家 ID 和页码" },
    en: { name: "Taobao shop catalog", description: "Read a page of products from a Taobao shop.", inputHint: "Shop ID, seller ID, and page" },
    example: { shop_id: "517932711", seller_id: "2200684271326", page: 1 },
  },
  {
    id: "tmall.sku-adjust", platform: "tmall", icon: "猫", credentialRequired: true,
    zh: { name: "天猫 SKU 调价", description: "使用保存的天猫 Cookie 查询 SKU 实时价格和库存。", inputHint: "输入 SKU ID，例如 6277426546603" },
    en: { name: "Tmall SKU price", description: "Use a saved Tmall cookie to retrieve a SKU price and stock.", inputHint: "Enter a SKU ID" },
    example: { sku_id: "6277426546603" },
  },
  {
    id: "jd.item", platform: "jd", icon: "京", credentialRequired: false,
    zh: { name: "京东商品详情", description: "通过已配置的数据网关查询单个京东商品。", inputHint: "输入京东商品 ID" },
    en: { name: "JD item details", description: "Fetch one JD item through the configured data gateway.", inputHint: "Enter a JD item ID" },
    example: { item_id: "10025990353889" },
  },
  {
    id: "jd.ware-business", platform: "jd", icon: "京", credentialRequired: true,
    zh: { name: "京东 wareBusiness", description: "使用浏览器刚捕获的签名 URL 查询 PC 商品业务数据。", inputHint: "SKU ID 和刚刚捕获的 signed_url" },
    en: { name: "JD wareBusiness", description: "Call the PC business endpoint with a freshly captured signed URL.", inputHint: "SKU ID and a freshly captured signed_url" },
    example: { sku_id: "10207466352379", signed_url: "https://api.m.jd.com/?functionId=pc_detailpage_wareBusiness&..." },
  },
];

export const crawlerById = (id: string) => crawlerCatalog.find((crawler) => crawler.id === id);
