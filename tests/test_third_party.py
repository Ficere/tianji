#!/usr/bin/env python3
"""Pinned, reproducible cross-checks against independent calculation engines."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fortune_calc import (  # noqa: E402
    analyze_person,
    calc_ascendant,
    calc_four_pillars,
    get_moon_sign,
    get_zodiac_precise,
    gregorian_to_jd,
)


CASES = [
    (1950, 1, 8, 2, 15),
    (1976, 9, 9, 17, 40),
    (1988, 12, 3, 19, 10),
    (1990, 5, 20, 8, 30),
    (1992, 8, 16, 14, 20),
    (2001, 3, 14, 6, 45),
    (2015, 2, 19, 12, 0),
    (2024, 2, 10, 9, 5),
]


def circular_error(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


class LunarPythonCrossValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from lunar_python import Solar
        except ImportError as exc:
            raise unittest.SkipTest("缺少测试依赖 lunar-python==1.4.8") from exc
        cls.Solar = Solar

    def test_four_pillars_match_pinned_lunar_python(self):
        for year, month, day, hour, minute in CASES:
            with self.subTest(date=(year, month, day, hour, minute)):
                eight = self.Solar.fromYmdHms(
                    year, month, day, hour, minute, 0
                ).getLunar().getEightChar()
                expected = [
                    eight.getYear(), eight.getMonth(),
                    eight.getDay(), eight.getTime(),
                ]
                self.assertEqual(
                    calc_four_pillars(year, month, day, hour, minute), expected
                )


class SwissEphemerisCrossValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import swisseph
        except ImportError as exc:
            raise unittest.SkipTest("缺少测试依赖 pysweph==2.10.3.6") from exc
        cls.swe = swisseph

    def test_sun_moon_and_ascendant_within_documented_tolerance(self):
        rows = [
            (1990, 5, 20, 8, 30, 39.9042, 116.4074, 8.0),
            (1992, 8, 16, 14, 20, 31.2304, 121.4737, 8.0),
            (1988, 12, 3, 19, 10, 30.5728, 104.0668, 8.0),
            (1990, 1, 20, 6, 0, 40.7128, -74.0060, -5.0),
        ]
        for year, month, day, hour, minute, lat, lon, tz in rows:
            with self.subTest(date=(year, month, day, hour, minute), tz=tz):
                jd_ut = gregorian_to_jd(year, month, day, hour, minute) - tz / 24
                sun_ref = self.swe.calc_ut(jd_ut, self.swe.SUN)[0][0]
                moon_ref = self.swe.calc_ut(jd_ut, self.swe.MOON)[0][0]
                asc_ref = self.swe.houses_ex(jd_ut, lat, lon, b"P")[1][0]

                sun_local = get_zodiac_precise(
                    year, month, day, hour, minute, tz
                )[2]
                moon_local = get_moon_sign(
                    year, month, day, hour, minute, tz
                )[3]
                asc_local = calc_ascendant(
                    year, month, day, hour, minute, lat, lon, tz
                )[1]

                self.assertLess(circular_error(sun_local, sun_ref), 0.05)
                self.assertLess(circular_error(moon_local, moon_ref), 0.15)
                self.assertLess(circular_error(asc_local, asc_ref), 0.05)

    def test_foreign_timezone_changes_boundary_results(self):
        # 纽约当地 1990-01-20 06:00 是水瓶座；历史实现硬编码 UTC+8，
        # 会把同一个钟表时间误判为摩羯座。
        corrected = get_zodiac_precise(1990, 1, 20, 6, 0, -5.0)[0]
        old_default = get_zodiac_precise(1990, 1, 20, 6, 0)[0]
        self.assertEqual(corrected, "水瓶座")
        self.assertEqual(old_default, "摩羯座")

        moon_corrected = get_moon_sign(1990, 1, 1, 6, 0, -5.0)[0]
        moon_old_default = get_moon_sign(1990, 1, 1, 6, 0)[0]
        self.assertEqual(moon_corrected, "双鱼座")
        self.assertEqual(moon_old_default, "水瓶座")

        integrated = analyze_person({
            "name": "测试者", "name_is_alias": True, "gender": "男",
            "solar_date": "1990-01-20", "birth_time": "06:00",
            "birth_city": "纽约",
        })
        self.assertEqual(integrated["zodiac"], "水瓶座")


class IztroCrossValidation(unittest.TestCase):
    MAJOR = {
        "紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府",
        "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
    }
    AUX = {
        "文昌", "文曲", "左辅", "右弼", "天魁", "天钺",
        "禄存", "擎羊", "陀罗", "火星", "铃星", "天马",
    }

    def test_ziwei_chart_matches_pinned_iztro(self):
        probe = ROOT / "tests" / "third_party" / "iztro_probe.js"
        if not (ROOT / "node_modules" / "iztro").exists():
            self.skipTest("缺少测试依赖；请运行 npm ci")
        cases = [
            {"date": "1990-05-20", "time": "08:30", "gender": "男"},
            {"date": "1992-08-16", "time": "14:20", "gender": "女"},
            {"date": "1988-12-03", "time": "19:10", "gender": "男"},
            {"date": "2001-03-14", "time": "06:45", "gender": "女"},
        ]
        completed = subprocess.run(
            ["node", str(probe)],
            input=json.dumps(cases, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=True,
            cwd=ROOT,
        )
        references = json.loads(completed.stdout)

        for case, reference in zip(cases, references, strict=True):
            with self.subTest(case=case):
                person = analyze_person({
                    "name": "张三",
                    "gender": case["gender"],
                    "solar_date": case["date"],
                    "birth_time": case["time"],
                    "birth_city": "北京",
                })
                ziwei = person["ziwei"]
                self.assertEqual(" ".join(person["bazi"]), reference["bazi"])
                self.assertEqual(ziwei["十二宫"]["命宫"], reference["lifePalace"])
                self.assertTrue(ziwei["身宫"].startswith(reference["bodyPalace"] + "宫"))
                self.assertEqual(ziwei["五行局"], reference["fiveElementsClass"])

                local_stars = {
                    **ziwei["十四主星落宫"], **ziwei["辅星落宫"]
                }
                for star in self.MAJOR | self.AUX:
                    self.assertEqual(
                        local_stars[star], reference["stars"][star], star
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
