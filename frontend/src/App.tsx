import { FormEvent, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

const Nav = () => {
  const { i18n, t } = useTranslation();
  return <nav><strong>{t("title")}</strong><span><Link to="/docs">{t("docs")}</Link><Link to="/playground">{t("dashboard")}</Link><Link to="/profiles">{t("profiles")}</Link><button onClick={() => i18n.changeLanguage(i18n.language === "zh-CN" ? "en-US" : "zh-CN")}>中 / EN</button></span></nav>;
};

const Home = () => <main className="hero"><Nav /><section className="glass"><p className="eyebrow">TAOBAO · TMALL · JD</p><h1>Secure crawler APIs for every workflow.</h1><p>JWT、API Token、加密 Cookie、代理档案与异步任务统一管理。</p><Link className="button" to="/docs">API Docs</Link></section></main>;

const Docs = () => <main className="page"><Nav /><h1>API Reference</h1><pre>{`POST /api/v1/crawls/tmall.sku-adjust
Authorization: Bearer <access-token>

{"input":{"sku_id":"6277426546603"},"credential_profile_id":1}

202 {"id":42,"status":"queued"}`}</pre></main>;

const Profiles = () => {
  const [cookie, setCookie] = useState("");
  const save = (event: FormEvent) => { event.preventDefault(); setCookie(""); };
  return <main className="page"><Nav /><h1>Credentials & Proxies</h1><form className="glass profile-form" onSubmit={save}><label>Cookie<textarea aria-label="Cookie" value={cookie} onChange={event => setCookie(event.target.value)} /></label><button>Save encrypted profile</button><p>The portal clears plaintext after submission; the API never returns saved secrets.</p></form></main>;
};

const Playground = () => <main className="page"><Nav /><h1>Crawler Playground</h1><section className="glass"><label>SKU ID<input defaultValue="6277426546603" /></label><button>Queue Tmall SKU job</button><p>Submit returns a job ID; poll <code>GET /api/v1/jobs/:id</code> until it succeeds.</p></section></main>;

export default function App() { return <Routes><Route path="/" element={<Home />} /><Route path="/docs" element={<Docs />} /><Route path="/profiles" element={<Profiles />} /><Route path="/playground" element={<Playground />} /></Routes>; }
