/** @type {import('@cucumber/cucumber').IConfiguration} */
export default {
  paths: ["features/**/*.feature"],
  import: ["support/world.ts", "support/hooks.ts", "steps/**/*.ts"],
  format: [
    "progress-bar",
    "html:reports/cucumber-report.html",
    "json:reports/cucumber-report.json",
  ],
  formatOptions: { snippetInterface: "async-await" },
  parallel: 1,
  timeout: 120_000,
  tags: "not @live",
};
