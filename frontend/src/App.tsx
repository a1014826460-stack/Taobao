import { Link, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

const Home = () => { const { t, i18n } = useTranslation(); return <main className="hero"><nav><strong>{t("title")}</strong><span><Link to="/docs">{t("docs")}</Link><button onClick={() => i18n.changeLanguage(i18n.language === "zh-CN" ? "en-US" : "zh-CN")}>中 / EN</button></span></nav><section className="glass"><p className="eyebrow">TAOBAO · TMALL · JD</p><h1>{t("subtitle")}</h1><p>JWT、API Token、加密 Cookie、代理档案与异步任务统一管理。</p><Link className="button" to="/docs">{t("docs")}</Link></section></main>; };
const Docs = () => <main className="page"><h1>API Reference</h1><pre>{`POST /api/v1/crawls/tmall.sku-adjust\nAuthorization: Bearer <access-token>\n\n{"input":{"sku_id":"6277426546603"},"credential_profile_id":1}\n\n202 {"id":42,"status":"queued"}`}</pre></main>;
export default function App() { return <Routes><Route path="/" element={<Home />} /><Route path="/docs" element={<Docs />} /></Routes>; }
