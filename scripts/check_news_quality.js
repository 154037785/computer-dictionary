const fs = require("fs");

function loadJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function textLength(text) {
  return String(text || "").replace(/\s+/g, "").length;
}

function containsAny(text, needles) {
  const value = String(text || "");
  return needles.some((needle) => value.includes(needle));
}

function hasMojibake(text) {
  return containsAny(text, [
    "\uFFFD",
    "\u951F\u65A4\u62F7",
    "\u9234",
    "\u95B3",
    "\u8139",
    "\u8137",
    "\u8292\u20AC",
    "\u6D93\uE15F",
    "\u934F\uE0C3",
    "\u93B6\u20AC",
    "\u5A11\u5806",
    "\u93C2\u677F",
    "\u675E\u6B22",
    "\u95C3",
    "\u9422",
  ]);
}

function hasTemplateTitle(title) {
  return /(\u6D88\u606F[\uFF1A:]|\u65B0\u52A8\u6001|^\u56FD\u9645.{0,16}\u6D88\u606F|^\u5916\u5A92.{0,16}\u6D88\u606F)/.test(title);
}

function hasTemplateSummary(summary) {
  return containsAny(summary, [
    "\u8FD9\u6761\u65B0\u95FB\u4E3B\u8981\u6D89\u53CA",
    "\u62A5\u9053\u91CD\u70B9",
    "\u5EFA\u8BAE\u7EE7\u7EED\u5173\u6CE8",
    "\u51FA\u73B0AI \u6A21\u578B\u6216\u667A\u80FD\u4F53\u80FD\u529B\u8FDB\u5C55",
    "\u4E3B\u8981\u5F71\u54CD\u65B9\u5411\u4E3A",
    "\u8FD9\u6761\u6D88\u606F\u9700\u8981\u653E\u5728",
  ]);
}

function checkDataset(path, label, options) {
  const data = loadJson(path);
  const items = data.items || [];
  const urls = new Set();
  const issues = [];

  if (items.length < options.minItems) {
    issues.push(`${label} has too few items: ${items.length}`);
  }

  for (const item of items) {
    const title = item.titleZh || item.title || "";
    const summary = item.summary || "";
    const source = item.source || "";
    const region = item.region || "";
    const url = item.url || "";

    if (!title || textLength(title) < 6) issues.push(`bad title: ${url}`);
    if (hasTemplateTitle(title)) issues.push(`template title: ${title}`);
    if (textLength(summary) < options.minSummaryLength) issues.push(`short summary ${textLength(summary)}: ${title}`);
    if (hasTemplateSummary(summary)) issues.push(`template summary: ${title}`);
    if (hasMojibake(title) || hasMojibake(summary) || hasMojibake(source) || hasMojibake(region)) {
      issues.push(`mojibake text: ${title}`);
    }
    if (url) {
      if (urls.has(url)) issues.push(`duplicate url: ${url}`);
      urls.add(url);
    }
  }

  return { count: items.length, issues };
}

const frontier = checkDataset("data/frontier-news.json", "frontier-news", {
  minItems: 12,
  minSummaryLength: 200,
});
const wechat = checkDataset("data/wechat-news.json", "wechat-news", {
  minItems: 12,
  minSummaryLength: 80,
});

console.log(JSON.stringify({ frontier, wechat }, null, 2));
if (frontier.issues.length || wechat.issues.length) {
  process.exitCode = 1;
}
