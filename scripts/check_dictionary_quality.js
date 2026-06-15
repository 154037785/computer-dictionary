const fs = require("fs");
const vm = require("vm");

const source = `${fs.readFileSync("app.js", "utf8")}\n;globalThis.__dict = dictionary;`;
const noop = () => {};

function elementStub() {
  return {
    innerHTML: "",
    textContent: "",
    value: "",
    hidden: false,
    href: "",
    dataset: {},
    style: {},
    classList: { toggle: noop, add: noop, remove: noop },
    addEventListener: noop,
    removeEventListener: noop,
    setAttribute: noop,
    removeAttribute: noop,
    focus: noop,
    scrollIntoView: noop,
    querySelector: () => elementStub(),
    querySelectorAll: () => [],
    appendChild: noop,
  };
}

const sandbox = {
  console,
  window: { addEventListener: noop, open: noop, scrollTo: noop },
  document: {
    addEventListener: noop,
    querySelector: () => elementStub(),
    querySelectorAll: () => [],
    getElementById: () => elementStub(),
    body: elementStub(),
    createElement: () => elementStub(),
  },
  navigator: { clipboard: { writeText: noop } },
  location: {},
  fetch() {
    return Promise.resolve({ ok: false, json: () => ({}) });
  },
  setTimeout,
  clearTimeout,
  requestAnimationFrame: (fn) => fn(),
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { timeout: 15000 });

const dictionary = sandbox.__dict || [];
const badSuffixes = [
  "\u6838\u5FC3\u6982\u5FF5",
  "\u5DE5\u4F5C\u673A\u5236",
  "\u7EC4\u6210\u7ED3\u6784",
  "\u5173\u952E\u6D41\u7A0B",
  "\u5E38\u89C1\u6307\u6807",
  "\u8BBE\u8BA1\u6743\u8861",
  "\u9519\u8BEF\u6A21\u5F0F",
  "\u6392\u969C\u65B9\u6CD5",
  "\u5B89\u5168\u8FB9\u754C",
  "\u5B9E\u8DF5\u573A\u666F",
];
const allTerms = [];
const nameCounts = new Map();
const explanationCounts = new Map();

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

for (const section of dictionary) {
  for (const term of section.terms || []) {
    const name = String(term.name || "").trim();
    const explanation = String(term.explanation || "").replace(/\s+/g, " ").trim();
    const image = String(term.image || "").replace(/\s+/g, " ").trim();
    allTerms.push({ ...term, sectionId: section.id, sectionTitle: section.title, name, explanation, image });
    if (name) nameCounts.set(name, (nameCounts.get(name) || 0) + 1);
    if (explanation) explanationCounts.set(explanation, (explanationCounts.get(explanation) || 0) + 1);
  }
}

const names = new Set(allTerms.map((term) => term.name));
const duplicates = [...nameCounts.entries()].filter(([, count]) => count > 1);
const repeatedExplanations = [...explanationCounts.entries()].filter(([, count]) => count > 1);
const lowValueNames = allTerms.filter((term) => badSuffixes.some((suffix) => term.name.endsWith(suffix)));
const missingCoreFields = allTerms.filter((term) => !term.name || !term.tag || !term.explanation || !term.image);
const missingEnglish = allTerms.filter((term) => !String(term.english || "").trim());
const shortExplanations = allTerms.filter((term) => term.explanation.length > 0 && term.explanation.length < 28);
const genericExplanations = allTerms.filter((term) => /\u53EA\u662F\u4E00\u4E2A\u96F6\u4EF6|\u91CD\u8981\u540D\u8BCD/.test(term.explanation) && term.explanation.length < 90);
const mojibakeTerms = allTerms.filter((term) =>
  hasMojibake(term.name) ||
  hasMojibake(term.tag) ||
  hasMojibake(term.explanation) ||
  hasMojibake(term.image) ||
  hasMojibake(term.english) ||
  hasMojibake(term.sectionTitle)
);
const missingRelations = [];

for (const term of allTerms) {
  for (const related of term.related || []) {
    if (!names.has(related)) {
      missingRelations.push({ term: term.name, related });
    }
  }
}

const bySection = dictionary.map((section) => ({
  id: section.id,
  title: section.title,
  count: (section.terms || []).length,
}));

const report = {
  totalTerms: allTerms.length,
  totalSections: dictionary.length,
  duplicates: duplicates.length,
  duplicateSamples: duplicates.slice(0, 20),
  lowValueNames: lowValueNames.length,
  repeatedExactExplanations: repeatedExplanations.length,
  missingCoreFields: missingCoreFields.length,
  missingEnglish: missingEnglish.length,
  shortExplanations: shortExplanations.length,
  genericShortExplanations: genericExplanations.length,
  mojibakeTerms: mojibakeTerms.length,
  mojibakeSamples: mojibakeTerms.slice(0, 20).map((term) => ({ section: term.sectionTitle, name: term.name })),
  missingRelations: missingRelations.length,
  missingRelationSamples: missingRelations.slice(0, 25),
  largestSections: [...bySection].sort((a, b) => b.count - a.count).slice(0, 12),
  smallestSections: [...bySection].sort((a, b) => a.count - b.count).slice(0, 12),
};

console.log(JSON.stringify(report, null, 2));

if (duplicates.length || lowValueNames.length || repeatedExplanations.length || missingCoreFields.length || missingEnglish.length || mojibakeTerms.length) {
  process.exitCode = 1;
}
