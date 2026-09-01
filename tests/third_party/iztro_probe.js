#!/usr/bin/env node
"use strict";

// A deliberately tiny adapter around the pinned iztro API. It reads a JSON
// array from stdin and emits only deterministic chart fields used by tests.
const fs = require("fs");
const { astro } = require("iztro");

function timeIndex(time) {
  const hour = Number(time.split(":")[0]);
  return hour === 23 ? 12 : Math.floor((hour + 1) / 2);
}

const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const result = cases.map((item) => {
  const chart = astro.bySolar(
    item.date.replaceAll("-", "/"),
    timeIndex(item.time),
    item.gender,
    true,
    "zh-CN"
  );
  const stars = {};
  for (const palace of chart.palaces) {
    for (const star of [...palace.majorStars, ...palace.minorStars]) {
      stars[star.name] = palace.earthlyBranch;
    }
  }
  return {
    bazi: chart.chineseDate,
    lifePalace: chart.earthlyBranchOfSoulPalace,
    bodyPalace: chart.earthlyBranchOfBodyPalace,
    fiveElementsClass: chart.fiveElementsClass,
    stars,
  };
});

process.stdout.write(JSON.stringify(result));
