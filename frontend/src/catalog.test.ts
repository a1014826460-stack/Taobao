import { describe, expect, it } from "vitest";

import { crawlerCatalog } from "./catalog";

describe("crawler catalog", () => {
  it("documents every public crawler in Chinese by default", () => {
    expect(crawlerCatalog).toHaveLength(5);
    expect(crawlerCatalog.every((crawler) => crawler.zh.name && crawler.example)).toBe(true);
  });
});
