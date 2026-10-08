#!/usr/bin/env python3
"""真太阳时排盘口径：时钟换算、四柱、紫微与独立引擎对照。"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fortune_calc import analyze_person, get_timezone_offset_hours, gregorian_to_jd  # noqa: E402


# (日期, 钟表时间, 纬度, 经度, 性别)：覆盖西部大幅修正、跨日、夏令时与东部小幅修正
CASES = [
    ("1996-08-20", "15:30", 22.01, 100.80, "男"),   # 景洪：未时（钟表为申时）
    ("2000-03-01", "00:40", 39.47, 75.99, "男"),    # 喀什：真太阳时跨回前一日
    ("1990-07-01", "09:10", 39.90, 116.41, "女"),   # 北京夏令时期间
    ("2015-06-10", "16:56", 39.92, 116.44, "男"),   # 北京：申时末段
    ("1985-11-20", "06:55", 45.75, 126.63, "女"),   # 哈尔滨：真太阳时快于钟表
    ("1978-01-05", "13:05", 29.65, 91.13, "男"),    # 拉萨：修正约 -2 小时
]


def person(date, time, lat, lon, gender, **extra):
    return analyze_person({
        "name": "测试", "name_is_alias": True, "gender": gender,
        "solar_date": date, "birth_time": time,
        "birth_lat": lat, "birth_lon": lon, **extra,
    })


def pillar_dt(result):
    pt = result["pillar_time"]
    return datetime.datetime.strptime(f"{pt['date']} {pt['time']}", "%Y-%m-%d %H:%M")


class TrueSolarClockTests(unittest.TestCase):
    def test_default_basis_is_true_solar(self):
        r = person(*CASES[0])
        self.assertEqual(r["pillar_time"]["basis"], "true_solar")
        self.assertEqual(r["pillar_time"]["time"], "14:09")
        self.assertEqual(r["bazi"][3], "辛未")

    def test_clock_basis_is_opt_in(self):
        r = person(*CASES[0], time_basis="clock")
        self.assertEqual(r["pillar_time"]["basis"], "clock")
        self.assertEqual(r["bazi"][3], "壬申")

    def test_cross_day_moves_day_pillar_and_lunar_day(self):
        r = person(*CASES[1])
        self.assertEqual(r["pillar_time"]["date"], "2000-02-29")
        self.assertEqual(r["bazi"][2], "丁巳")
        clock = person(*CASES[1], time_basis="clock")
        self.assertEqual(clock["bazi"][2], "戊午")
        self.assertNotEqual(r["lunar_day"], clock["lunar_day"])

    def test_china_dst_is_honored(self):
        offset = get_timezone_offset_hours(39.9, 116.4, 1990, 7, 1, 9, 10)[0]
        self.assertEqual(offset, 9.0)
        self.assertEqual(get_timezone_offset_hours(39.9, 116.4, 1990, 12, 1, 9, 10)[0], 8.0)
        self.assertEqual(get_timezone_offset_hours(39.9, 116.4, 1994, 7, 1, 9, 10)[0], 8.0)
        r = person(*CASES[2])
        self.assertEqual(r["pillar_time"]["instant_beijing_time"], "1990-07-01 08:10")
        self.assertIn("CN_DST_APPLIED", [w["code"] for w in r["warnings"]])

    def test_xinjiang_still_uses_beijing_clock(self):
        self.assertEqual(get_timezone_offset_hours(39.47, 75.99, 2000, 3, 1, 0, 40)[0], 8.0)

    def test_missing_location_degrades_loudly(self):
        r = analyze_person({"name": "测试", "name_is_alias": True, "gender": "男",
                            "solar_date": "2000-03-01", "birth_time": "00:40"})
        self.assertEqual(r["pillar_time"]["basis"], "clock")
        self.assertIn("TRUE_SOLAR_UNAVAILABLE", [w["code"] for w in r["warnings"]])

    def test_coordinates_override_city_name(self):
        r = analyze_person({"name": "测试", "name_is_alias": True, "gender": "男",
                            "solar_date": "1996-08-20", "birth_time": "15:30",
                            "birth_city": "云南省西双版纳州景洪市",
                            "birth_lat": 22.01, "birth_lon": 100.80})
        self.assertEqual(r["birth_city"], "云南省西双版纳州景洪市")
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["bazi"][3], "辛未")


class SwissEphemerisTrueSolarTests(unittest.TestCase):
    """真太阳时 = UT + 经度/15 + 均时差；均时差取自 Swiss Ephemeris。"""

    @classmethod
    def setUpClass(cls):
        try:
            import swisseph
        except ImportError as exc:
            raise unittest.SkipTest("缺少测试依赖 pysweph==2.10.3.6") from exc
        cls.swe = swisseph

    def test_true_solar_time_within_one_minute(self):
        for date, time, lat, lon, gender in CASES:
            with self.subTest(date=date, time=time, lon=lon):
                r = person(date, time, lat, lon, gender)
                y, m, d = map(int, date.split("-"))
                hh, mm = map(int, time.split(":"))
                tz = r["pillar_time"]["clock_tz_offset_hours"]
                jd_ut = gregorian_to_jd(y, m, d, hh, mm) - tz / 24
                eot_days = self.swe.time_equ(jd_ut)
                eot_days = eot_days[0] if isinstance(eot_days, tuple) else eot_days
                lat_jd = jd_ut + lon / 360.0 + eot_days
                ref = datetime.datetime(2000, 1, 1, 12) + datetime.timedelta(days=lat_jd - 2451545.0)
                diff_min = abs((pillar_dt(r) - ref).total_seconds()) / 60
                self.assertLess(diff_min, 1.0, f"{date} {time}: {pillar_dt(r)} vs {ref}")


class LunarPythonTrueSolarTests(unittest.TestCase):
    """日柱/时柱用真太阳时钟，年柱/月柱用出生瞬间，与 lunar-python 分别对照。"""

    @classmethod
    def setUpClass(cls):
        try:
            from lunar_python import Solar
        except ImportError as exc:
            raise unittest.SkipTest("缺少测试依赖 lunar-python==1.4.8") from exc
        cls.Solar = Solar

    def test_four_pillars_match_independent_engine(self):
        for date, time, lat, lon, gender in CASES:
            with self.subTest(date=date, time=time):
                r = person(date, time, lat, lon, gender)
                inst = datetime.datetime.strptime(
                    r["pillar_time"]["instant_beijing_time"], "%Y-%m-%d %H:%M")
                pdt = pillar_dt(r)
                e_inst = self.Solar.fromYmdHms(inst.year, inst.month, inst.day,
                                               inst.hour, inst.minute, 0).getLunar().getEightChar()
                e_pil = self.Solar.fromYmdHms(pdt.year, pdt.month, pdt.day,
                                              pdt.hour, pdt.minute, 0).getLunar().getEightChar()
                self.assertEqual(r["bazi"][:2], [e_inst.getYear(), e_inst.getMonth()])
                self.assertEqual(r["bazi"][2:], [e_pil.getDay(), e_pil.getTime()])


class IztroTrueSolarTests(unittest.TestCase):
    MAJOR = {"紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府",
             "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"}
    AUX = {"文昌", "文曲", "左辅", "右弼", "天魁", "天钺",
           "禄存", "擎羊", "陀罗", "火星", "铃星", "天马"}

    def test_ziwei_matches_iztro_on_true_solar_clock(self):
        if not (ROOT / "node_modules" / "iztro").exists():
            self.skipTest("缺少测试依赖；请运行 npm ci")
        results = [person(*c) for c in CASES]
        probes = [{"date": r["pillar_time"]["date"], "time": r["pillar_time"]["time"],
                   "gender": c[4]} for r, c in zip(results, CASES)]
        completed = subprocess.run(
            ["node", str(ROOT / "tests" / "third_party" / "iztro_probe.js")],
            input=json.dumps(probes, ensure_ascii=False), text=True,
            capture_output=True, check=True, cwd=ROOT)
        refs = json.loads(completed.stdout)
        for r, ref, probe in zip(results, refs, probes):
            with self.subTest(probe=probe):
                zw = r["ziwei"]
                self.assertEqual(zw["十二宫"]["命宫"], ref["lifePalace"])
                self.assertTrue(zw["身宫"].startswith(ref["bodyPalace"] + "宫"))
                self.assertEqual(zw["五行局"], ref["fiveElementsClass"])
                local = {**zw["十四主星落宫"], **zw["辅星落宫"]}
                for star in self.MAJOR | self.AUX:
                    self.assertEqual(local[star], ref["stars"][star], star)


class RegionalTimezoneTests(unittest.TestCase):
    def test_xinjiang_follows_beijing_dst(self):
        self.assertEqual(get_timezone_offset_hours(39.47, 75.99, 1990, 7, 1, 10, 0)[0], 9.0)

    def test_hong_kong_and_taipei_do_not_inherit_mainland_dst(self):
        self.assertEqual(get_timezone_offset_hours(22.30, 114.17, 1990, 7, 1, 10, 0)[:2], (8.0, "Asia/Hong_Kong"))
        self.assertEqual(get_timezone_offset_hours(25.03, 121.56, 1990, 7, 1, 10, 0)[:2], (8.0, "Asia/Taipei"))

    def test_hong_kong_without_timezonefinder_is_estimated_not_mainland(self):
        import fortune_calc
        saved = fortune_calc._TF_INSTANCE
        fortune_calc._TF_INSTANCE = None
        try:
            offset, zone, estimated = get_timezone_offset_hours(22.30, 114.17, 1990, 7, 1, 10, 0)
            self.assertEqual((offset, zone, estimated), (8.0, "Asia/Hong_Kong", True))
            self.assertEqual(get_timezone_offset_hours(39.90, 116.40, 1990, 7, 1, 10, 0)[0], 9.0)
        finally:
            fortune_calc._TF_INSTANCE = saved

    def test_neighbours_inside_china_bbox_use_their_own_zone(self):
        import fortune_calc
        if fortune_calc._TF_INSTANCE is None:
            self.skipTest("需要 timezonefinder")
        for lat, lon, expected in [(37.57, 126.98, 9.0), (33.59, 130.40, 9.0),
                                   (21.03, 105.85, 7.0), (28.61, 77.21, 5.5)]:
            with self.subTest(lat=lat, lon=lon):
                self.assertEqual(get_timezone_offset_hours(lat, lon, 2000, 1, 1, 10, 0)[0], expected)

    def test_dst_warning_only_for_mainland(self):
        seoul = person("2000-01-01", "10:00", 37.57, 126.98, "男")
        self.assertNotIn("CN_DST_APPLIED", [w["code"] for w in seoul["warnings"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
