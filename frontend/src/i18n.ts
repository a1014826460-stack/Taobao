import i18n from "i18next";
import { initReactI18next } from "react-i18next";

i18n.use(initReactI18next).init({
  lng: "zh-CN",
  fallbackLng: "en-US",
  resources: {
    "zh-CN": { translation: { title: "Crawler API", subtitle: "安全、可观察的爬虫 API 平台", docs: "API 文档", dashboard: "控制台", profiles: "凭据与代理" } },
    "en-US": { translation: { title: "Crawler API", subtitle: "Secure, observable crawler APIs", docs: "Documentation", dashboard: "Dashboard", profiles: "Credentials & Proxies" } },
  },
});

export default i18n;
