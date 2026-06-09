const fs = require("fs");

function loadJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function textLength(text) {
  return String(text || "").replace(/\s+/g, "").length;
}

function hasMojibake(text) {
  return /(�|锟斤拷|鈥|閳|脙|脗|芒|涓|鍏|鎶€|寮€|娑堟|鏂板|杩欐|鏈哄|闃|缁滄)/.test(String(text || ""));
}

function checkDataset(path, label, options) {
  const data = loadJson(path);
  const items = data.items || [];
  const urls = new Set();
  const issues = [];
  const forbiddenTitle = /(消息[：:：]|新动态|^国际.{0,16}消息|^外媒.{0,16}消息)/;
  const forbiddenSummary = /(这条新闻主要涉及|报道重点|建议继续关注|出现AI 模型或智能体能力进展|主要影响方向为|这条消息需要放在)/;

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
    if (forbiddenTitle.test(title)) issues.push(`template title: ${title}`);
    if (textLength(summary) < options.minSummaryLength) issues.push(`short summary ${textLength(summary)}: ${title}`);
    if (forbiddenSummary.test(summary)) issues.push(`template summary: ${title}`);
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
