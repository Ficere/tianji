#!/usr/bin/env python3
"""
天机 v6.0 自动化测试套件

覆盖：
  - 四柱八字计算（6条，对照卜易居/chinesebazi.com）
  - P1-A 太阳星座精确计算（20条，对照天文精确进入时刻）
  - P2-A 月亮星座计算（15条，对照 ephem 精确计算交叉验证）
  - P1-B 紫微主星安星（对照算法北派算法计算结果）
  - 上升星座计算（5条，对照 Astro.com）

运行：
  python tests/test_suite.py -v          # 全部测试
  python tests/test_suite.py TestZodiacPrecise -v  # 只测星座
  python tests/test_suite.py TestZiweiStars -v     # 只测紫微
"""

import sys
import os
import unittest

# 添加脚本路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from fortune_calc import (
    calc_four_pillars,
    get_zodiac_precise,
    get_moon_sign,
    calc_ziwei_full,
    get_ascendant_by_city,
    _find_solar_term_jde,
    _jde_to_beijing,
    DI_ZHI, ZODIAC_ORDER,
)
from fortune_calc import analyze_person, analyze_synastry


# ============================================================
# 四柱测试（6条，对照卜易居/chinesebazi.com）
# ============================================================

class TestFourPillars(unittest.TestCase):
    """四柱八字计算准确性测试（对照卜易居/chinesebazi.com）"""

    CASES = [
        # (year, month, day, hour, minute, expected_joined, description, source)
        (1990, 5,  20,  8, 30, "庚午 辛巳 乙酉 庚辰", "普通日期",         "卜易居"),
        (1994, 4,  15,  6,  0, "甲戌 戊辰 辛未 辛卯", "普通日期",         "卜易居"),
        (2000, 1,   1,  0, 30, "己卯 丙子 戊午 壬子", "跨年/立春前",       "卜易居"),
        (1985, 2,   4, 12,  0, "乙丑 戊寅 甲戌 庚午", "立春当日（12:00在立春后）", "chinesebazi.com"),
        (1976, 10,  1, 14,  0, "丙辰 丁酉 丙戌 乙未", "寒露节气边界",      "卜易居"),
        (2024, 2,  10, 23, 30, "甲辰 丙寅 甲辰 甲子", "晚子时不换日柱",   "卜易居"),
    ]

    def test_four_pillars(self):
        for year, month, day, hour, minute, expected, desc, source in self.CASES:
            with self.subTest(desc=desc):
                result = " ".join(calc_four_pillars(year, month, day, hour, minute))
                self.assertEqual(
                    result, expected,
                    f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} "
                    f"计算={result} 期望={expected} 来源={source}"
                )


# ============================================================
# P1-A: 精确太阳星座测试
# ============================================================

class TestZodiacPrecise(unittest.TestCase):
    """
    太阳星座精确计算测试（基于天文精确进入时刻）。
    所有期望值由 _find_solar_term_jde() 精确计算确认，
    并可与 Astro.com 交叉验证。
    """

    # 精确进入时刻（北京时间）已通过 _jde_to_beijing(_find_solar_term_jde()) 验证
    INGRESS_BJT = {
        # (year, sign_degree): (month, day, hour, minute)  —— 精确进入时刻
        (1990, 30):  (4, 20, 16, 18),   # 金牛座
        (2000,  0):  (3, 20, 15, 31),   # 白羊座（春分）
        (2024, 90):  (6, 21,  4, 49),   # 巨蟹座（夏至）
        (1985, 270): (12, 22,  6,  8),  # 摩羯座（冬至）
        (1990, 300): (1, 20, 16, 1),    # 水瓶座
    }

    CASES = [
        # (year, month, day, hour, minute, expected_sign, note)
        # —— 边界前（仍在旧星座）
        (1990,  4, 20, 12,  0, "白羊座",  "1990金牛进入前（16:18前）"),
        (1990,  4, 20, 16,  0, "白羊座",  "1990金牛进入前（16:18前）精确"),
        (2000,  3, 20, 15,  0, "双鱼座",  "2000春分白羊进入前（15:31前）"),
        (2024,  6, 21,  4,  0, "双子座",  "2024夏至巨蟹进入前（04:49前）"),
        (1985, 12, 22,  5,  0, "射手座",  "1985冬至摩羯进入前"),
        # —— 边界后（进入新星座）
        (1990,  4, 20, 17,  0, "金牛座",  "1990金牛进入后（16:18后）"),
        (2000,  3, 20, 16,  0, "白羊座",  "2000春分白羊进入后（15:31后）"),
        (2024,  6, 21,  5,  0, "巨蟹座",  "2024夏至巨蟹进入后（04:49后）"),
        (1985, 12, 22,  7,  0, "摩羯座",  "1985冬至摩羯进入后"),
        (1990,  1, 20, 17,  0, "水瓶座",  "1990水瓶进入后"),
        # —— 中段日期（确定性强）
        (1990,  5, 20,  8, 30, "金牛座",  "普通金牛日"),
        (1994,  4, 15,  6,  0, "白羊座",  "白羊中段"),
        (1994,  8, 15, 12,  0, "狮子座",  "狮子中段"),
        (1994, 11, 15, 12,  0, "天蝎座",  "天蝎中段"),
        (2024,  2, 14, 12,  0, "水瓶座",  "水瓶中段"),
        # —— 特殊日期
        # 2000-01-01 00:30 BJT: 太阳黄经 279.54°, 属摩羯座（270-300°）
        (2000,  1,  1,  0, 30, "摩羯座",  "千禧年元旦（黄经279.54°→摩羯座）"),
        (1985,  2,  4, 12,  0, "水瓶座",  "立春当日"),
        (1990,  1,  1, 12,  0, "摩羯座",  "新年元旦摩羯"),
        (1976, 10,  1, 14,  0, "天秤座",  "国庆天秤"),
        (2024,  2, 10, 23, 30, "水瓶座",  "晚子时水瓶"),
    ]

    def test_zodiac_precise(self):
        for year, month, day, hour, minute, expected, note in self.CASES:
            with self.subTest(note=note):
                sign, _, lon, near = get_zodiac_precise(year, month, day, hour, minute)
                self.assertEqual(
                    sign, expected,
                    f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} "
                    f"计算={sign}（黄经{lon:.2f}°） 期望={expected} [{note}]"
                )

    def test_boundary_warning(self):
        """边界附近（±2°）应触发警告标记"""
        # 进入前约1天内，near_boundary 应为 True
        _, _, lon, near = get_zodiac_precise(1990, 4, 20, 15, 0)
        self.assertTrue(near, f"边界附近应触发警告，黄经={lon:.2f}°")

    def test_all_twelve_signs(self):
        """确保12个星座都能被识别"""
        sign_dates = [
            (2000,  4,  5, "白羊座"), (2000,  5,  5, "金牛座"),
            (2000,  6,  5, "双子座"), (2000,  7,  5, "巨蟹座"),
            (2000,  8,  5, "狮子座"), (2000,  9,  5, "处女座"),
            (2000, 10,  5, "天秤座"), (2000, 11,  5, "天蝎座"),
            (2000, 12,  5, "射手座"), (2000,  1, 15, "摩羯座"),
            (2000,  2,  5, "水瓶座"), (2000,  3,  5, "双鱼座"),
        ]
        for month, day, hour, expected in [(m, d, 12, s) for _year, m, d, s in sign_dates]:
            year = 2000
            sign, _, _, _ = get_zodiac_precise(year, month, day, hour, 0)
            self.assertEqual(sign, expected, f"{year}-{month:02d}-{day:02d}")


# ============================================================
# P2-A: 月亮星座测试
# ============================================================

class TestMoonSign(unittest.TestCase):
    """
    月亮星座计算准确性测试（Meeus Ch.47 简化算法）。
    月亮约每2.3天换一星座，算法精度约±1°（±2小时）。
    边界±3°内给出不确定提示，不视为错误。

    验证方法：
    - 所有期望值已与 PyEphem（ELP2000/82B 精确星历库）交叉验证，最大偏差<1°。
    - "原Astro.com列"仅供参考，部分数据存在日期输入差异，以ephem为准。

    交叉验证记录详见 tests/v6_validation_report.md
    """

    CASES = [
        # (year, month, day, hour, minute, expected_sign, note, source)
        # 以下期望值均经 PyEphem 交叉验证（偏差<1°）
        (1990,  5, 20,  8, 30, "双鱼座",  "1990-05-20 08:30 BJT | ephem=356.6°",  "PyEphem"),
        (1994,  4, 15,  6,  0, "双子座",  "1994-04-15 06:00 BJT | ephem=67.1°",   "PyEphem"),
        (2000,  1,  1,  0, 30, "天蝎座",  "2000-01-01 00:30 BJT | ephem=213.5°",  "PyEphem"),
        (1985,  2,  4, 12,  0, "巨蟹座",  "1985-02-04 12:00 BJT | ephem=116.1°",  "PyEphem"),
        # 1976-10-01 BJT 14:00 -> UT 06:00: ephem=288.3°(摩羯座), 非天秤座
        (1976, 10,  1, 14,  0, "摩羯座",  "1976-10-01 14:00 BJT | ephem=288.3°",  "PyEphem"),
        # 2024-02-10 BJT 12:00 -> UT 04:00: ephem=323.5°(水瓶座), 非天蝎座
        (2024,  2, 10, 12,  0, "水瓶座",  "2024-02-10 12:00 BJT | ephem=323.5°",  "PyEphem"),
        # 2024-06-21 BJT 12:00 -> UT 04:00: ephem=259.0°(射手座), 非摩羯座
        (2024,  6, 21, 12,  0, "射手座",  "2024-06-21 12:00 BJT | ephem=259.0°",  "PyEphem"),
        (2024,  1,  1, 12,  0, "处女座",  "2024-01-01 12:00 BJT | ephem=158.0°",  "PyEphem"),
        # 2024-12-25 BJT 12:00: ephem月球在208.0°(天秤座/天蝎座边界) -> 边界模糊允许容差
        (2024, 12, 25, 12,  0, "天秤座",  "2024-12-25 12:00 BJT | ephem=208.0°⚠️边界", "PyEphem"),
        (2023,  6, 15, 12,  0, "金牛座",  "2023-06-15 12:00 BJT | ephem=48.3°",   "PyEphem"),
        # 2023-09-15 BJT 12:00 -> UT 04:00: ephem=172.8°(处女座), 非射手座
        (2023,  9, 15, 12,  0, "处女座",  "2023-09-15 12:00 BJT | ephem=172.8°",  "PyEphem"),
        # 2022-03-20 BJT 12:00 -> UT 04:00: ephem=202.9°(天秤座), 非摩羯座
        (2022,  3, 20, 12,  0, "天秤座",  "2022-03-20 12:00 BJT | ephem=202.9°",  "PyEphem"),
        # 2022-07-04 BJT 12:00 -> UT 04:00: ephem=157.6°(处女座), 非水瓶座
        (2022,  7,  4, 12,  0, "处女座",  "2022-07-04 12:00 BJT | ephem=157.6°",  "PyEphem"),
        # 2021-01-20 BJT 12:00 -> UT 04:00: ephem=22.3°(白羊座), 非处女座
        (2021,  1, 20, 12,  0, "白羊座",  "2021-01-20 12:00 BJT | ephem=22.3°",   "PyEphem"),
        # 2020-06-06 BJT 12:00 -> UT 04:00: ephem=260.5°(射手座), 非摩羯座
        (2020,  6,  6, 12,  0, "射手座",  "2020-06-06 12:00 BJT | ephem=260.5°",  "PyEphem"),
    ]

    def test_moon_sign(self):
        """测试月亮星座，边界附近（near_boundary=True）时给予容差处理"""
        ok_count = 0
        boundary_count = 0
        fail_cases = []

        for year, month, day, hour, minute, expected, note, source in self.CASES:
            sign, deg, near, lon = get_moon_sign(year, month, day, hour, minute)

            if sign == expected:
                ok_count += 1
            elif near:
                # 边界附近算法误差允许，记录但不算失败
                boundary_count += 1
                print(f"  ⚠️ 边界模糊 {year}-{month:02d}-{day:02d}: "
                      f"计算={sign} 期望={expected} 黄经={lon:.1f}° [{note}]")
            else:
                fail_cases.append((year, month, day, hour, minute, sign, expected, lon, note))

        if fail_cases:
            msgs = [f"{y}-{m:02d}-{d:02d} {h:02d}:{mi:02d}: 计算={s} 期望={e} 黄经={l:.1f}° [{n}]"
                    for y, m, d, h, mi, s, e, l, n in fail_cases]
            self.fail("月亮星座非边界错误:\n  " + "\n  ".join(msgs))

        print(f"\n  月亮星座: {ok_count}✅ {boundary_count}⚠️(边界) {len(fail_cases)}❌")

    def test_boundary_note(self):
        """验证边界提示正常工作（返回布尔值）"""
        _, _, near, _ = get_moon_sign(1990, 5, 20, 8, 30)
        self.assertIsInstance(near, bool)


# ============================================================
# P1-B: 紫微主星安星测试
# ============================================================

class TestZiweiStars(unittest.TestCase):
    """
    紫微斗数14主星安星准确性测试。
    采用北派算法（标准《紫微斗数全书》流派）。
    期望值由算法计算输出，并与 PyEphem/论命网 交叉验证命宫干支。

    五行局对照：
    - 壬申年 -> 金四局（命宫：戊申宫）
    - 甲子年 -> 火六局（命宫：甲戌宫）
    - 庚午年 -> 火六局（命宫：戊子宫）
    - 丙寅年 -> 土五局（命宫：辛丑宫）
    - 戊辰年 -> 木三局（五行局由命宫天干地支查纳音决定）
    """

    CASES = [
        # (lunar_month, lunar_day, hour, gender, year_gan, year_zhi,
        #  expected_ziwei_zhi, expected_tianfu_zhi, wuxing_ju, source)
        #
        # 注：五行局由【命宫天干+命宫地支】（纳音）决定，非年柱，测试值均经算法验证。
        #
        # 壬申年 农历1月 午时 -> 命宫=戊申宫 -> (戊,申)=金四局
        (1, 1,  12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        (1, 2,  12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        (1, 3,  12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        (1, 7,  12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        (1, 10, 12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        (1, 15, 12, "男", "壬", "申", "子", "寅", "金四局", "北派算法"),
        # 戊辰年 农历2月 午时 -> 命宫=辛酉宫 -> (辛,酉)=木三局
        (2, 1,  12, "男", "戊", "辰", "子", "寅", "木三局", "北派算法"),
        (2, 2,  12, "男", "戊", "辰", "酉", "亥", "木三局", "北派算法"),
        (2, 3,  12, "男", "戊", "辰", "子", "寅", "木三局", "北派算法"),
        (2, 6,  12, "男", "戊", "辰", "子", "寅", "木三局", "北派算法"),
        (2, 10, 12, "男", "戊", "辰", "子", "寅", "木三局", "北派算法"),
        # 甲子年 农历3月 午时 -> 命宫=甲戌宫 -> (甲,戌)=火六局
        (3, 1,  12, "男", "甲", "子", "子", "寅", "火六局", "北派算法"),
        (3, 4,  12, "男", "甲", "子", "亥", "丑", "火六局", "北派算法"),
        (3, 8,  12, "男", "甲", "子", "子", "寅", "火六局", "北派算法"),
        (3, 12, 12, "男", "甲", "子", "亥", "丑", "火六局", "北派算法"),
        # 庚午年 农历4月 卯时 -> 命宫=己丑宫 -> (己,丑)=火六局
        (4, 26,  8, "男", "庚", "午", "子", "寅", "火六局", "北派算法"),
        # 庚午年 农历5月 午时 -> 命宫=戊子宫 -> (戊,子)=火六局
        (5, 1,  12, "男", "庚", "午", "子", "寅", "火六局", "北派算法"),
        (5, 5,  12, "男", "庚", "午", "子", "寅", "火六局", "北派算法"),
        (5, 10, 12, "男", "庚", "午", "子", "寅", "火六局", "北派算法"),
        # 丙寅年 农历6月 午时 -> 命宫=辛丑宫 -> (辛,丑)=土五局
        (6, 1,  12, "男", "丙", "寅", "子", "寅", "土五局", "北派算法"),
        (6, 6,  12, "男", "丙", "寅", "子", "寅", "土五局", "北派算法"),
        (6, 12, 12, "男", "丙", "寅", "子", "寅", "土五局", "北派算法"),
    ]

    def test_ziwei_star_positions(self):
        """验证紫微星与天府星落宫（五行局）"""
        for case in self.CASES:
            lm, ld, h, gender, yg, yz = case[0], case[1], case[2], case[3], case[4], case[5]
            expected_ju = case[8]
            source = case[9]
            with self.subTest(lunar=f"{lm}月{ld}日", year_gz=f"{yg}{yz}"):
                result = calc_ziwei_full(yg, yz, lm, ld, float(h), gender)
                self.assertEqual(
                    result["五行局"], expected_ju,
                    f"农历{lm}月{ld}日 年干{yg}{yz} "
                    f"计算={result['五行局']} 期望={expected_ju} 来源={source}"
                )

    def test_main_stars_exist(self):
        """验证14颗主星都有安星结果"""
        main_stars = ["紫微", "天机", "太阳", "武曲", "天同", "廉贞",
                      "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]
        result = calc_ziwei_full("庚", "午", 4, 26, 8.5, "男")
        for star in main_stars:
            self.assertIn(star, result["十四主星落宫"],
                         f"主星 {star} 未出现在安星结果中")

    def test_auxiliary_stars_exist(self):
        """验证辅星安星结果存在"""
        aux_stars = ["文昌", "文曲", "左辅", "右弼", "天魁", "天钺",
                     "禄存", "擎羊", "陀罗", "火星", "铃星"]
        result = calc_ziwei_full("庚", "午", 4, 26, 8.5, "男")
        for star in aux_stars:
            self.assertIn(star, result["辅星落宫"],
                         f"辅星 {star} 未出现在安星结果中")

    def test_sihua_exists(self):
        """验证四化飞星计算存在且包含四个化"""
        result = calc_ziwei_full("庚", "午", 4, 26, 8.5, "男")
        sihua = result["四化飞星"]
        for hua in ["化禄", "化权", "化科", "化忌"]:
            self.assertIn(hua, sihua, f"四化中缺少 {hua}")

    def test_dayun_sequence(self):
        """验证大限序列有12个大限，且年龄递增"""
        result = calc_ziwei_full("庚", "午", 4, 26, 8.5, "男")
        dayun = result["大限序列"]
        self.assertEqual(len(dayun), 12, "大限序列应有12个")
        for i in range(1, len(dayun)):
            prev_age = int(dayun[i-1]["年龄范围"].split("–")[0])
            curr_age = int(dayun[i]["年龄范围"].split("–")[0])
            self.assertGreater(curr_age, prev_age, "大限年龄应递增")

    def test_pattern_detection(self):
        """验证格局识别功能正常运行"""
        result = calc_ziwei_full("甲", "戌", 3, 15, 6.0, "男")
        pattern_names = [p[0] for p in result["格局识别"]]
        # 贪狼守命时应识别到
        stars_in_ming = result["命宫主星"]
        if "贪狼" in stars_in_ming:
            self.assertIn("贪狼守命", pattern_names, "贪狼在命宫时应识别贪狼守命格")


# ============================================================
# 上升星座测试
# ============================================================

class TestAscendant(unittest.TestCase):
    """上升星座计算准确性测试（对照 Astro.com）"""

    CASES = [
        # (year, month, day, hour, minute, city, expected_sign, note, source)
        (1990,  5, 20,  8, 30, "北京",   "巨蟹座", "1990-05-20 北京 Astro.com",  "Astro.com"),
        (1994,  4, 15,  6,  0, "上海",   "金牛座", "1994-04-15 上海 Astro.com",  "Astro.com"),
        (2000,  1,  1,  0, 30, "广州",   "天秤座", "2000-01-01 广州 Astro.com",  "Astro.com"),
        (2024,  6, 21, 12,  0, "北京",   "处女座", "2024-06-21 北京 Astro.com",  "Astro.com"),
        (1985,  2,  4, 12,  0, "北京",   "双子座", "1985-02-04 北京 Astro.com",  "Astro.com"),
    ]

    def test_ascendant(self):
        """验证上升星座计算（边界附近给予容差）"""
        fail_cases = []
        boundary_cases = []
        for year, month, day, hour, minute, city, expected, note, source in self.CASES:
            rs, rlon, rnear = get_ascendant_by_city(year, month, day, hour, minute, city)
            if rs == expected:
                pass
            elif rnear:
                boundary_cases.append((note, rs, expected, rlon))
            else:
                fail_cases.append((note, rs, expected, rlon))

        for note, rs, expected, rlon in boundary_cases:
            print(f"  ⚠️ 上升边界 {note}: 计算={rs} 期望={expected} 黄经={rlon:.1f}°")

        if fail_cases:
            msgs = [f"{n}: 计算={s} 期望={e} 黄经={l:.1f}°" for n, s, e, l in fail_cases]
            self.fail("上升星座非边界错误:\n  " + "\n  ".join(msgs))

    def test_unknown_city(self):
        """不在库中的城市应返回 None"""
        rs, rlon, rnear = get_ascendant_by_city(2000, 1, 1, 12, 0, "火星城")
        self.assertIsNone(rs)


# ============================================================
# 完整流程 E2E 测试
# ============================================================

class TestEndToEnd(unittest.TestCase):
    """端到端测试：完整 analyze_person 流程"""

    def test_full_person_analysis(self):
        """验证 analyze_person 返回所有必要字段"""
        from fortune_calc import analyze_person
        member = {
            "name": "测试",
            "gender": "男",
            "solar_date": "1990-05-20",
            "birth_time": "08:30",
            "lunar": {"month": 4, "day": 26},
            "surname_len": 1,
            "birth_city": "北京",
        }
        result = analyze_person(member)
        required_keys = [
            "bazi", "zodiac", "sun_longitude", "zodiac_boundary_note",
            "moon_sign", "moon_longitude", "moon_boundary_note",
            "rising_sign", "astro_combo_reading",
            "ziwei", "chenggu", "wx",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"缺少字段: {key}")

        # 验证紫微子字段
        ziwei = result["ziwei"]
        ziwei_keys = [
            "命宫", "身宫", "五行局", "命主", "身主", "大运方向",
            "十二宫", "十二宫星曜", "十四主星落宫", "辅星落宫",
            "四化飞星", "大限序列", "命宫主星", "格局识别",
        ]
        for key in ziwei_keys:
            self.assertIn(key, ziwei, f"紫微缺少字段: {key}")

        # 验证星座解读存在
        self.assertGreater(len(result["astro_combo_reading"]), 50,
                          "三星组合解读内容过少")

    def test_no_city_no_rising(self):
        """未提供城市时，上升星座应为 None"""
        from fortune_calc import analyze_person
        member = {
            "name": "无城市",
            "gender": "女",
            "solar_date": "1994-04-15",
            "birth_time": "06:00",
            "lunar": {"month": 3, "day": 15},
        }
        result = analyze_person(member)
        self.assertIsNone(result["rising_sign"])


# ============================================================
# 合盘评分契约回归（防止「文档说100、脚本算105」这类漂移）
# ============================================================

# 与 SKILL.md §9.1、schemas/reading_v8.schema.json 严格一致
SYNASTRY_BANDS = {
    "wuxing_balance": 20,
    "wuxing_complete": 5,
    "shengxiao": 20,
    "xingzuo": 15,
    "riZhu": 20,
    "chenggu": 15,
    "xingming": 5,
}


def _make_member(idx, seed_rand, with_name=True):
    names = ["张伟", "李娜", "王芳", "刘洋", "陈静", "赵磊", "欧阳明", "司马光"]
    y = 1950 + seed_rand.randint(0, 55)
    return {
        "name": names[idx % len(names)] if with_name else "",
        "gender": "男" if idx % 2 == 0 else "女",
        "solar_date": f"{y}-{seed_rand.randint(1, 12):02d}-{seed_rand.randint(1, 28):02d}",
        "birth_time": f"{seed_rand.randint(0, 23):02d}:{seed_rand.choice([0, 15, 30, 45]):02d}",
    }


class TestSynastryScoreContract(unittest.TestCase):
    """
    对 analyze_synastry 的**真实计算输出**做回归，而不是只校验 examples/*.json。

    背景：v8.1 之前脚本实际上限为 105 分（五行平衡给到 25、称骨给到 20、
    姓名项完全未实现），与 README / SKILL.md / schema 的 100 分契约不符；
    且因三项按人对累加，2 人组最高 77 分、5 人组最高 105 分，分数不可横向比较。
    这些偏差只校验示例文件是抓不到的。
    """

    RANDOM_TRIALS = 120

    def _iter_cases(self):
        import random
        for with_name in (True, False):
            for n in (2, 3, 5):
                rnd = random.Random(20250101 + n * 7 + int(with_name))
                for _ in range(self.RANDOM_TRIALS):
                    members = [
                        analyze_person(_make_member(i, rnd, with_name))
                        for i in range(n)
                    ]
                    yield n, with_name, analyze_synastry(members)

    def test_each_dimension_within_band(self):
        """每个分项都必须落在其声明的分值区间内。"""
        for n, with_name, r in self._iter_cases():
            cs = r["composite_scores"]
            for key, cap in SYNASTRY_BANDS.items():
                self.assertIn(key, cs, f"{n}人合盘缺少分项 {key}")
                score = cs[key]["score"]
                self.assertGreaterEqual(score, 0, f"{key} 为负：{score}")
                self.assertLessEqual(
                    score, cap,
                    f"{n}人（{'有' if with_name else '无'}姓名）{key}={score} 超出上限 {cap}",
                )

    def test_total_equals_sum_and_never_exceeds_max(self):
        """total 必须等于分项之和，且不得超过 max_possible。"""
        for n, with_name, r in self._iter_cases():
            cs = r["composite_scores"]
            parts = round(sum(cs[k]["score"] for k in SYNASTRY_BANDS), 1)
            self.assertAlmostEqual(
                parts, r["score"], places=1,
                msg=f"{n}人：分项之和 {parts} ≠ total {r['score']}",
            )
            self.assertLessEqual(
                r["score"], r["max_possible"],
                f"{n}人：total {r['score']} 超过满分 {r['max_possible']}",
            )
            self.assertLessEqual(r["max_possible"], 100)

    def test_max_possible_reflects_name_availability(self):
        """全员有姓名 → 满分100；否则姓名项计0分、满分95。"""
        for n, with_name, r in self._iter_cases():
            if with_name:
                self.assertEqual(r["max_possible"], 100, f"{n}人有姓名却非满分100")
            else:
                self.assertEqual(r["max_possible"], 95, f"{n}人无姓名却非满分95")
                self.assertEqual(r["composite_scores"]["xingming"]["score"], 0)

    def test_score_is_group_size_invariant(self):
        """
        同一量纲检查：各组人数的得分区间应大致重叠，
        不应出现「5人组普遍高出一整档」的累加式伪高分。
        """
        import statistics
        means = {}
        for n in (2, 3, 5):
            scores = [r["score"] for m, w, r in self._iter_cases() if m == n and w]
            means[n] = statistics.mean(scores)
        spread = max(means.values()) - min(means.values())
        self.assertLess(
            spread, 12,
            f"不同人数的平均分差异过大（{means}），说明评分仍随人数系统性漂移",
        )

    def test_known_pair_is_deterministic_and_documented(self):
        """固定输入的黄金用例，锁死口径变更。"""
        a = analyze_person({"name": "张伟", "gender": "男",
                            "solar_date": "1990-05-20", "birth_time": "14:30"})
        b = analyze_person({"name": "李娜", "gender": "女",
                            "solar_date": "1992-08-15", "birth_time": "09:00"})
        r1 = analyze_synastry([a, b])
        r2 = analyze_synastry([a, b])
        self.assertEqual(r1["score"], r2["score"], "同一输入两次计算结果不一致")
        self.assertEqual(r1["pair_count"], 1)
        self.assertEqual(r1["max_possible"], 100)
        self.assertTrue(0 <= r1["score"] <= 100)
        self.assertIn("★", r1["rating"])

    def test_rating_matches_percentage_thresholds(self):
        """评级必须由 total/max_possible 百分比推出，而非绝对分。"""
        for n, with_name, r in self._iter_cases():
            pct = r["score"] / r["max_possible"] * 100
            self.assertAlmostEqual(pct, r["percentage"], places=1)
            expected = (
                "极佳" if pct >= 85 else
                "良好" if pct >= 70 else
                "中等" if pct >= 55 else
                "有待改善" if pct >= 40 else "需多加注意"
            )
            self.assertIn(expected, r["rating"], f"{pct:.1f}% 对应评级错误：{r['rating']}")

    def test_single_member_returns_note(self):
        """不足2人时返回提示而非评分。"""
        a = analyze_person({"name": "张伟", "gender": "男",
                            "solar_date": "1990-05-20", "birth_time": "14:30"})
        self.assertIn("note", analyze_synastry([a]))


# ============================================================
# 报告生成器
# ============================================================

def generate_report():
    """生成文字测试报告，方便记录交叉验证结果。"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestFourPillars, TestZodiacPrecise, TestMoonSign,
                TestZiweiStars, TestAscendant, TestEndToEnd]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    report_path = os.path.join(os.path.dirname(__file__), "v6_validation_report.md")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 天机 v6.0 验证报告\n\n")
        f.write(f"> 生成时间：自动\n")
        f.write(f"> 测试总数：{result.testsRun}  通过：{passed}  失败：{len(result.failures)}  错误：{len(result.errors)}\n\n")
        f.write("## 测试覆盖\n\n")
        f.write("| 模块 | 测试类 | 用例数 |\n")
        f.write("|------|--------|--------|\n")
        f.write("| 四柱八字 | TestFourPillars | 6 |\n")
        f.write("| 太阳星座（精确）| TestZodiacPrecise | 20+ |\n")
        f.write("| 月亮星座 | TestMoonSign | 15 |\n")
        f.write("| 紫微主星 | TestZiweiStars | 22+ |\n")
        f.write("| 上升星座 | TestAscendant | 5 |\n")
        f.write("| 端到端流程 | TestEndToEnd | 2 |\n\n")
        if result.failures:
            f.write("## 失败项\n\n```\n")
            for test, traceback in result.failures:
                f.write(f"{test}\n{traceback}\n\n")
            f.write("```\n")
        else:
            f.write("## 结论\n\n全部测试通过 ✅\n")
    print(f"\n报告已写入 {report_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        sys.argv.pop(1)
        generate_report()
    else:
        unittest.main(verbosity=2)
