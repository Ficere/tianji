#!/usr/bin/env python3
"""
天机 · 深层分析层 (v8.2)

在既有排盘结果之上补三块「解读深度」，**不新增任何报告章节**：

  1. analyze_canggan_shishen  地支藏干十神 + 人元司令分野 + 通根质量
  2. analyze_zhi_relations    刑冲合会（六合/三合/三会/六冲/相刑/相害/相破/天干五合）
  3. analyze_day_master       日主强弱量化（生扶 vs 克泄耗加权比值）
  4. determine_yongshen       用神/喜忌判定（扶抑为主、调候为辅，带流派声明与置信度）
  5. cross_validate           八字 / 紫微 / 姓名 / 星座 四系统一致性检测

设计约束：
  - **全部产出属于计算层**，供叙事层加深理解，不得逐条誊写进最终报告。
  - 每个判断都必须给出 `basis`（依据）与 `confidence`（置信度）。
    命理各家分歧极大，宁可显式披露分歧，也不输出伪确定性结论。
"""

from collections import Counter

# ============================================================
# 基础常量
# ============================================================

TIAN_GAN = list("甲乙丙丁戊己庚辛壬癸")
DI_ZHI = list("子丑寅卯辰巳午未申酉戌亥")

WU_XING_GAN = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
               "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WU_XING_ZHI = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
               "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
YIN_YANG_GAN = {"甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
                "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"}

# 藏干按「本气 → 中气 → 余气」排列
CANG_GAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 人元司令分野（各支内藏干轮流当令的日数，自节令起算）
SI_LING_FEN_YE = {
    "子": [("壬", 10), ("癸", 20)],
    "丑": [("癸", 9), ("辛", 3), ("己", 18)],
    "寅": [("戊", 7), ("丙", 7), ("甲", 16)],
    "卯": [("甲", 10), ("乙", 20)],
    "辰": [("乙", 9), ("癸", 3), ("戊", 18)],
    "巳": [("戊", 7), ("庚", 7), ("丙", 16)],
    "午": [("丙", 10), ("己", 9), ("丁", 11)],
    "未": [("丁", 9), ("乙", 3), ("己", 18)],
    "申": [("戊", 7), ("壬", 7), ("庚", 16)],
    "酉": [("庚", 10), ("辛", 20)],
    "戌": [("辛", 9), ("丁", 3), ("戊", 18)],
    "亥": [("戊", 7), ("甲", 7), ("壬", 16)],
}

# 气的层级与权重（本气 / 中气 / 余气）
QI_LEVELS = ["本气", "中气", "余气"]
QI_WEIGHT = {"本气": 1.0, "中气": 0.5, "余气": 0.25}

# 柱位权重：月令最重，其次日支（日主自坐），再时支、年支
PILLAR_WEIGHT = {"年": 0.8, "月": 1.5, "日": 1.2, "时": 1.0}
PILLAR_NAMES = ["年", "月", "日", "时"]

# 十神归类
SHENG_FU_SHISHEN = {"比肩", "劫财", "正印", "偏印"}          # 生扶日主
KE_XIE_HAO_SHISHEN = {"食神", "伤官", "正财", "偏财", "正官", "七杀"}  # 克泄耗

# ---- 地支关系表 ----
LIU_HE = {frozenset(p): hua for p, hua in [
    (("子", "丑"), "土"), (("寅", "亥"), "木"), (("卯", "戌"), "火"),
    (("辰", "酉"), "金"), (("巳", "申"), "水"), (("午", "未"), "土"),
]}
SAN_HE_GROUPS = {("申", "子", "辰"): "水", ("寅", "午", "戌"): "火",
                 ("巳", "酉", "丑"): "金", ("亥", "卯", "未"): "木"}
SAN_HUI_GROUPS = {("寅", "卯", "辰"): "木", ("巳", "午", "未"): "火",
                  ("申", "酉", "戌"): "金", ("亥", "子", "丑"): "水"}
LIU_CHONG = {frozenset(p) for p in [
    ("子", "午"), ("丑", "未"), ("寅", "申"),
    ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]}
XIANG_HAI = {frozenset(p) for p in [
    ("子", "未"), ("丑", "午"), ("寅", "巳"),
    ("卯", "辰"), ("申", "亥"), ("酉", "戌")]}
XIANG_XING = {
    frozenset(("寅", "巳")): "无恩之刑", frozenset(("巳", "申")): "无恩之刑",
    frozenset(("寅", "申")): "无恩之刑", frozenset(("丑", "戌")): "恃势之刑",
    frozenset(("戌", "未")): "恃势之刑", frozenset(("丑", "未")): "恃势之刑",
    frozenset(("子", "卯")): "无礼之刑",
}
# 三刑全备（子卯为二支相刑，不属「三刑全备」，仍走两两判定）
SAN_XING_GROUPS = {
    ("寅", "巳", "申"): "无恩之刑",
    ("丑", "戌", "未"): "恃势之刑",
}

# 合/冲的分量差着数倍，基调不能只数条目数
HE_WEIGHT = {"三会": 1.5, "三合": 1.2, "六合": 0.6, "半合": 0.6}
# 合化成局时对「化神」五行的力量加成。
# 只在「化神得令」时施加——古法「合而不化」者众，不得令的合局不改变五行格局。
HUA_BONUS = {"三会": 1.5, "三合": 1.2, "半合": 0.5, "六合": 0.3, "天干五合": 0.4}
CHONG_WEIGHT = {"三刑": 1.5, "六冲": 1.0, "相刑": 0.7, "自刑": 0.5,
                "相害": 0.4, "相破": 0.3}

ZI_XING = {"辰", "午", "酉", "亥"}  # 自刑：同支相见
XIANG_PO = {frozenset(p) for p in [
    ("子", "酉"), ("午", "卯"), ("申", "巳"),
    ("寅", "亥"), ("辰", "丑"), ("戌", "未")]}
TIAN_GAN_HE = {frozenset(p): hua for p, hua in [
    (("甲", "己"), "土"), (("乙", "庚"), "金"), (("丙", "辛"), "水"),
    (("丁", "壬"), "木"), (("戊", "癸"), "火")]}

# 季节 → 调候基调
DONG_MONTHS = {"亥", "子", "丑"}   # 寒
XIA_MONTHS = {"巳", "午", "未"}    # 燥热


def get_shishen(day_gan, other_gan):
    """十神：以日主为我，判断另一天干与我的关系。"""
    day_wx, other_wx = WU_XING_GAN[day_gan], WU_XING_GAN[other_gan]
    same_yy = YIN_YANG_GAN[day_gan] == YIN_YANG_GAN[other_gan]
    if day_wx == other_wx:
        return "比肩" if same_yy else "劫财"
    if SHENG[day_wx] == other_wx:
        return "食神" if same_yy else "伤官"
    if SHENG[other_wx] == day_wx:
        return "偏印" if same_yy else "正印"
    if KE[day_wx] == other_wx:
        return "偏财" if same_yy else "正财"
    if KE[other_wx] == day_wx:
        return "七杀" if same_yy else "正官"
    return "未知"


def _is_adjacent(pos_label_str):
    """位置标签形如「年月」「月日」「年时」。相邻两柱作用力全发，隔位打折。"""
    order = "年月日时"
    if not pos_label_str or len(pos_label_str) != 2:
        return True
    a, b = pos_label_str[0], pos_label_str[1]
    if a not in order or b not in order:
        return True
    return abs(order.index(a) - order.index(b)) == 1


def _ke_of(element):
    """返回克该五行者。KE[a]==b 表示 a 克 b，故须反查。"""
    return next((k for k, v in KE.items() if v == element), None)


def _sheng_of(element):
    """返回生该五行者。"""
    return next((k for k, v in SHENG.items() if v == element), None)


def _shishen_of_element(day_gan, element):
    """某五行相对日主属于哪一类十神（不分阴阳，返回类别名）。"""
    day_wx = WU_XING_GAN[day_gan]
    if element == day_wx:
        return "比劫"
    if SHENG[element] == day_wx:
        return "印绶"
    if SHENG[day_wx] == element:
        return "食伤"
    if KE[day_wx] == element:
        return "财星"
    if KE[element] == day_wx:
        return "官杀"
    return "未知"

import datetime as _dt


# ============================================================
# 1. 地支藏干十神 + 人元司令
# ============================================================

def _si_ling_gan(month_zhi, days_into_month):
    """
    人元司令：自节令起算第 N 日，该月支内当令的藏干。

    days_into_month 为 None（无法确定节令日差）时退回本气，
    并在返回值中标记 estimated=True，供置信度计算下调。
    """
    fenye = SI_LING_FEN_YE.get(month_zhi)
    if not fenye:
        return None, True
    if days_into_month is None:
        # 退回本气。本气是分野序列的**末段**（余气→中气→本气按日推移），
        # 也是该支占日最多、最具代表性的一段，取首段会误取上月余气。
        return fenye[-1][0], True
    acc = 0
    for gan, days in fenye:
        acc += days
        if days_into_month < acc:
            return gan, False
    return fenye[-1][0], False


def analyze_canggan_shishen(bazi, day_gan, days_into_month=None):
    """
    展开四支藏干的十神，并标注本气/中气/余气、人元司令、是否为日主之根。

    这是本次升级的数据底座：原先 shishen 只有 4 个天干十神，
    而 12 个藏干的十神信息一直被丢弃，导致「财藏于库」「官星无根」
    这类关键结构完全看不见。
    """
    month_zhi = bazi[1][1]
    si_ling, si_ling_estimated = _si_ling_gan(month_zhi, days_into_month)
    day_wx = WU_XING_GAN[day_gan]

    pillars = []
    for idx, pillar in enumerate(bazi):
        gan, zhi = pillar[0], pillar[1]
        pos = PILLAR_NAMES[idx]
        hidden = []
        cg_list = CANG_GAN.get(zhi, [])
        # 分野与藏干出自不同传承，四正之支（子午卯酉）及亥的司令干可能不在藏干表内：
        #   子月壬、卯月甲、午月丙、酉月庚 —— 与本气同五行异阴阳，可归位到本气；
        #   亥月戊 —— 土，与亥所藏壬甲异五行，无从归位，此时不加司令权重并如实标注。
        si_ling_host = None
        if pos == "月" and si_ling:
            if si_ling in cg_list:
                si_ling_host = si_ling
            else:
                si_ling_host = next(
                    (c for c in cg_list if WU_XING_GAN[c] == WU_XING_GAN[si_ling]), None)
        for qi_idx, cg in enumerate(cg_list):
            qi = QI_LEVELS[qi_idx] if qi_idx < len(QI_LEVELS) else "余气"
            cg_wx = WU_XING_GAN[cg]
            is_si_ling = (pos == "月" and cg == si_ling_host)
            # 通根：藏干与日主同五行（比劫根）或生日主（印根）
            root_type = None
            if cg_wx == day_wx:
                root_type = "比劫根"
            elif SHENG[cg_wx] == day_wx:
                root_type = "印根"
            hidden.append({
                "干": cg,
                "五行": cg_wx,
                "气": qi,
                "十神": get_shishen(day_gan, cg),
                "司令": is_si_ling,
                "日主之根": root_type,
                # 该藏干在全局的力量权重（柱位 × 气 × 司令加成）
                "力量": round(
                    PILLAR_WEIGHT[pos] * QI_WEIGHT[qi] * (1.5 if is_si_ling else 1.0), 3
                ),
            })
        pillars.append({
            "柱": pos,
            "干支": pillar,
            "天干十神": "日主" if idx == 2 else get_shishen(day_gan, gan),
            "藏干": hidden,
        })

    # 通根汇总：日主有根与否，是判断从格 / 身弱的第一道关口
    roots = [
        {"柱": p["柱"], "支": p["干支"][1], "干": h["干"], "气": h["气"],
         "类型": h["日主之根"], "力量": h["力量"]}
        for p in pillars for h in p["藏干"] if h["日主之根"]
    ]
    root_power = round(sum(r["力量"] for r in roots), 3)
    if root_power >= 1.5:
        root_quality = "根深"
    elif root_power >= 0.6:
        root_quality = "有根"
    elif root_power > 0:
        root_quality = "根浅"
    else:
        root_quality = "无根"

    return {
        "月令司令": {
            "干": si_ling,
            "五行": WU_XING_GAN[si_ling] if si_ling else None,
            "十神": get_shishen(day_gan, si_ling) if si_ling else None,
            "按本气估算": si_ling_estimated,
            # 司令干是否落在月支藏干内。False 表示该段司令之气不由本支承载
            #（如亥月首七日戊土司令），此时不加 1.5 倍司令权重，避免虚增月令力量。
            "入藏干": si_ling in CANG_GAN.get(month_zhi, []) if si_ling else False,
        },
        "四柱藏干": pillars,
        "日主通根": {
            "质量": root_quality,
            "根力合计": root_power,
            "明细": roots,
        },
    }


# ============================================================
# 2. 刑冲合会
# ============================================================

def analyze_zhi_relations(bazi):
    """
    地支刑冲合会 + 天干五合。

    只报告**实际成立**的关系，不成立的一律不占篇幅。
    合会局额外标注是否「化神得令」，因为不得令的合局多半合而不化。
    """
    zhis = [p[1] for p in bazi]
    gans = [p[0] for p in bazi]
    month_zhi = zhis[1]
    month_wx = WU_XING_ZHI[month_zhi]
    items = []

    def pos_label(i, j):
        return f"{PILLAR_NAMES[i]}{PILLAR_NAMES[j]}"

    # --- 三会方（力量最大，优先判定）---
    for group, wx in SAN_HUI_GROUPS.items():
        if all(z in zhis for z in group):
            items.append({
                "类型": "三会", "关系": f"{''.join(group)}会{wx}局", "五行": wx,
                "位置": "全局", "强度": "极强",
                "化神得令": wx == month_wx,
                "说明": f"三会{wx}方，该五行力量在全局占绝对优势",
            })

    # --- 三合局（全合 / 半合）---
    for group, wx in SAN_HE_GROUPS.items():
        present = [z for z in group if z in zhis]
        if len(present) == 3:
            items.append({
                "类型": "三合", "关系": f"{''.join(group)}合{wx}局", "五行": wx,
                "位置": "全局", "强度": "强", "化神得令": wx == month_wx,
                "说明": f"三合{wx}局成，{wx}势聚而有力",
            })
        elif len(present) == 2 and group[1] in present:
            # 半合须带旺神（三合局中神），否则不论
            items.append({
                "类型": "半合", "关系": f"{''.join(present)}半合{wx}", "五行": wx,
                "位置": "局部", "强度": "中", "化神得令": wx == month_wx,
                "说明": f"半合{wx}，力量弱于三合，需岁运引动",
            })

    # --- 三刑全备（寅巳申 / 丑戌未）---
    # 三支俱全时作用力远大于两两相刑，须合并为一条；
    # 否则寅巳申会被拆成寅巳、巳申、寅申三条（有重复地支时更多），
    # 令「刑冲数」虚高，进而污染总体基调与置信度。
    san_xing_members = set()
    for group, gname in SAN_XING_GROUPS.items():
        if all(z in zhis for z in group):
            san_xing_members |= set(group)
            items.append({
                "类型": "三刑", "关系": f"{''.join(group)}三刑（{gname}）",
                "位置": "全局", "强度": "极强",
                "说明": f"{gname}全备，主刑伤、官非、反复纠缠，力远过两两相刑",
            })

    # --- 两两关系 ---
    for i in range(4):
        for j in range(i + 1, 4):
            z1, z2 = zhis[i], zhis[j]
            fs = frozenset((z1, z2))
            adjacent = (j - i == 1)
            if z1 == z2:
                if z1 in ZI_XING:
                    items.append({
                        "类型": "自刑", "关系": f"{z1}{z2}自刑", "五行": WU_XING_ZHI[z1],
                        "位置": pos_label(i, j), "强度": "弱",
                        "说明": "自刑主内耗、自我消磨，非外来冲击",
                    })
                continue
            if fs in LIU_HE:
                hua = LIU_HE[fs]
                items.append({
                    "类型": "六合", "关系": f"{z1}{z2}合{hua}", "五行": hua,
                    "位置": pos_label(i, j), "强度": "中",
                    "化神得令": hua == month_wx,
                    "说明": "六合主牵绊、结合，得令则化、不得令则合而不化",
                })
            if fs in LIU_CHONG:
                items.append({
                    "类型": "六冲", "关系": f"{z1}{z2}相冲",
                    "位置": pos_label(i, j),
                    "强度": "强" if adjacent else "中",
                    "说明": ("紧邻相冲，冲力全发，主变动、分离、健康隐患"
                             if adjacent else "隔位相冲，冲力打折"),
                })
            if fs in XIANG_XING and not (z1 in san_xing_members and z2 in san_xing_members):
                items.append({
                    "类型": "相刑", "关系": f"{z1}{z2}相刑（{XIANG_XING[fs]}）",
                    "位置": pos_label(i, j), "强度": "中",
                    "说明": "刑主纠缠、是非、伤损，比冲更绵长隐蔽",
                })
            if fs in XIANG_HAI:
                items.append({
                    "类型": "相害", "关系": f"{z1}{z2}相害",
                    "位置": pos_label(i, j), "强度": "弱",
                    "说明": "害主暗损、猜忌，作用力最轻，需其他条件配合方显",
                })
            if fs in XIANG_PO:
                items.append({
                    "类型": "相破", "关系": f"{z1}{z2}相破",
                    "位置": pos_label(i, j), "强度": "弱",
                    "说明": "破主破损、半途而废，古法中作用力最轻",
                })

    # --- 天干五合 ---
    for i in range(4):
        for j in range(i + 1, 4):
            fs = frozenset((gans[i], gans[j]))
            if len(fs) == 2 and fs in TIAN_GAN_HE:
                hua = TIAN_GAN_HE[fs]
                involves_day = (i == 2 or j == 2)
                items.append({
                    "类型": "天干五合", "关系": f"{gans[i]}{gans[j]}合化{hua}",
                    "五行": hua, "位置": pos_label(i, j), "强度": "中",
                    "化神得令": hua == month_wx,
                    "涉及日主": involves_day,
                    "说明": ("日主被合，主意志易受牵制、行事需他人成全"
                             if involves_day else "他干相合，主该两柱所代表的人事关系紧密"),
                })

    # 汇总：合会 vs 刑冲，是判断命局「稳定 or 动荡」的直接指标
    # 天干合另计：它作用于「意志层」，与地支的「环境层」不同质，混在一起会稀释信号
    gan_he = sum(1 for it in items if it["类型"] == "天干五合")
    harmony = sum(1 for it in items if it["类型"] in ("三会", "三合", "半合", "六合"))
    conflict = sum(1 for it in items
                   if it["类型"] in ("六冲", "三刑", "相刑", "相害", "相破", "自刑"))

    # 基调不能只数条目：六冲与相破的分量差着数倍，
    # 且「隔位」比「紧邻」要打折。故另算加权合力/冲力，由它决定基调。
    he_power = round(sum(HE_WEIGHT.get(it["类型"], 0) *
                         (0.6 if it.get("位置") not in ("全局", "局部") and
                          not _is_adjacent(it.get("位置")) else 1.0)
                         for it in items
                         if it["类型"] in ("三会", "三合", "半合", "六合")), 2)
    chong_power = round(sum(CHONG_WEIGHT.get(it["类型"], 0) *
                            (0.6 if it.get("位置") not in ("全局",) and
                             not _is_adjacent(it.get("位置")) else 1.0)
                            for it in items
                            if it["类型"] in ("六冲", "三刑", "相刑", "相害",
                                              "相破", "自刑")), 2)

    if chong_power == 0 and he_power == 0:
        tone = "平静无合无冲，命局结构松散，外力牵动小"
    elif max(chong_power, he_power) < 1.0:
        # 只有零星隔位轻作用时，比例再悬殊也谈不上「显著」
        tone = "仅见零星轻微作用，地支之间牵动有限，格局主要取决于五行本身的旺衰"
    elif chong_power > he_power * 1.3:
        tone = "刑冲之力显著过合会，命局动荡、变动频繁，宜以稳制动"
    elif he_power > chong_power * 1.3:
        tone = "合会之力显著过刑冲，命局黏合度高，稳定但也易受牵绊难以脱身"
    else:
        tone = "合冲之力相当，命局张力明显，成败常在一念之间"

    return {"关系列表": items, "合会数": harmony, "刑冲数": conflict,
            "天干合数": gan_he, "合力": he_power, "冲力": chong_power,
            "总体基调": tone}


# ============================================================
# 3. 日主强弱量化
# ============================================================

def analyze_day_master(bazi, canggan_detail, relations=None):
    """
    以「生扶力量 vs 克泄耗力量」的加权比值量化日主强弱。

    评分口径（完全透明、可复现）：
      - 日主自身固定计 1.2 分生扶
      - 年/月/时三天干各计 1.0 分，按十神归入生扶或克泄耗
      - 每个藏干计「柱位权重 × 气权重 × 司令加成(1.5)」
      - 合化成局且化神得令者，按 HUA_BONUS 计入对应一方
      - strength = 生扶 / (生扶 + 克泄耗) × 100，50 为中和基准
    """
    day_gan = bazi[2][0]
    sheng_fu = 1.2   # 日主自身
    ke_xie_hao = 0.0
    basis = [f"日主 {day_gan} 自身 +1.2（生扶）"]

    for idx, pillar in enumerate(bazi):
        if idx == 2:
            continue
        ss = get_shishen(day_gan, pillar[0])
        if ss in SHENG_FU_SHISHEN:
            sheng_fu += 1.0
            basis.append(f"{PILLAR_NAMES[idx]}干 {pillar[0]}（{ss}）+1.0 生扶")
        elif ss in KE_XIE_HAO_SHISHEN:
            ke_xie_hao += 1.0
            basis.append(f"{PILLAR_NAMES[idx]}干 {pillar[0]}（{ss}）+1.0 克泄耗")

    for p in canggan_detail["四柱藏干"]:
        for h in p["藏干"]:
            w = h["力量"]
            if h["十神"] in SHENG_FU_SHISHEN:
                sheng_fu += w
                if w >= 0.6:
                    basis.append(
                        f"{p['柱']}支{p['干支'][1]}藏{h['干']}（{h['十神']}·{h['气']}"
                        f"{'·司令' if h['司令'] else ''}）+{w} 生扶")
            elif h["十神"] in KE_XIE_HAO_SHISHEN:
                ke_xie_hao += w
                if w >= 0.6:
                    basis.append(
                        f"{p['柱']}支{p['干支'][1]}藏{h['干']}（{h['十神']}·{h['气']}"
                        f"{'·司令' if h['司令'] else ''}）+{w} 克泄耗")

    # 合化局：得令方化，其化神五行须计入强弱，否则「三会火局」这类
    # 足以改写格局的结构在强弱判定中完全隐形。
    day_wx_self = WU_XING_GAN[day_gan]
    if relations:
        for it in relations["关系列表"]:
            bonus = HUA_BONUS.get(it["类型"])
            hua_wx = it.get("五行")
            if not (bonus and it.get("化神得令") and hua_wx):
                continue
            if hua_wx == day_wx_self or SHENG[hua_wx] == day_wx_self:
                sheng_fu += bonus
                basis.append(f"{it['关系']}·化神得令 +{bonus} 生扶")
            else:
                ke_xie_hao += bonus
                basis.append(f"{it['关系']}·化神得令 +{bonus} 克泄耗")

    total = sheng_fu + ke_xie_hao
    score = round(sheng_fu / total * 100, 1) if total else 50.0

    if score >= 65:
        label = "身强"
    elif score >= 56:
        label = "偏强"
    elif score >= 45:
        label = "中和"
    elif score >= 35:
        label = "偏弱"
    else:
        label = "身弱"

    # 月令得失：判断强弱最重的单一因素，单列以便叙事层引用
    si_ling_ss = canggan_detail["月令司令"]["十神"]
    de_ling = si_ling_ss in SHENG_FU_SHISHEN
    root_quality = canggan_detail["日主通根"]["质量"]

    # 特殊格局预警（从格/专旺格不适用常规扶抑，必须显式提示）
    # 判从格的关键不只是「弱」，还要看天干有无印比透出来救——
    # 只要有一个印或比劫透干通根，从格即破，仍按常规扶抑论。
    gan_rescue = [
        f"{PILLAR_NAMES[i]}干{p[0]}（{get_shishen(day_gan, p[0])}）"
        for i, p in enumerate(bazi)
        if i != 2 and get_shishen(day_gan, p[0]) in SHENG_FU_SHISHEN
    ]
    special = None
    if score < 25 and root_quality in ("无根", "根浅"):
        if not gan_rescue:
            special = (f"疑似从弱格（从财/从杀/从儿）：日主{root_quality}且极弱（{score}），"
                       f"天干亦无印比接应，常规扶抑法可能得出完全相反的结论")
        else:
            special = (f"日主极弱（{score}）但{'、'.join(gan_rescue)}透出救应，从格不成立，"
                       f"仍按扶抑论；惟用神与日主俱弱，成败高度依赖岁运")
    elif score > 85:
        special = "疑似专旺/从强格：满盘印比，常规抑制法可能引发反激"
    elif score > 82 and not de_ling:
        special = "日主极旺却不得令，旺而无根基，格局判定各家分歧较大"

    return {
        "强弱分": score,
        "标签": label,
        "生扶力量": round(sheng_fu, 3),
        "克泄耗力量": round(ke_xie_hao, 3),
        "得令": de_ling,
        "通根质量": root_quality,
        "特殊格局预警": special,
        "计分依据": basis,
    }


# ============================================================
# 4. 用神 / 喜忌判定
# ============================================================

def _tiaohou(day_gan, month_zhi):
    """
    调候（气候平衡）判定。

    这里只做**有明确共识的部分**：冬月需火暖局、夏月需水润局。
    其余月份调候需求弱，交由扶抑主导——不编造完整的穷通宝鉴 120 格表。
    """
    day_wx = WU_XING_GAN[day_gan]
    if month_zhi in DONG_MONTHS:
        note = f"生于{month_zhi}月，天寒地冻，非火不暖"
        if day_wx == "水":
            note += "；水日主生冬月尤寒，见火方能生机流动"
        elif day_wx == "木":
            note += "；木日主生冬月为寒木，须丙火向阳方可条达"
        return {"元素": "火", "需求": "强", "说明": note}
    if month_zhi in XIA_MONTHS:
        note = f"生于{month_zhi}月，火土燥烈，非水不润"
        if day_wx == "火":
            note += "；火日主生夏月过于炎上，须壬癸济之"
        elif day_wx == "土":
            note += "；土日主生夏月为焦土，得水方能载物"
        return {"元素": "水", "需求": "强", "说明": note}
    if month_zhi in ("辰", "戌"):
        return {"元素": None, "需求": "弱",
                "说明": f"生于{month_zhi}月，土气当权而气候尚平，调候需求不迫切，以扶抑为主"}
    return {"元素": None, "需求": "无",
            "说明": f"生于{month_zhi}月，寒暖适中，调候非急务，以扶抑定用神"}


def _element_powers(bazi, canggan_detail, relations=None):
    """
    全局五行力量分布（天干各1.0，藏干按权重），用于判断用神是否有力。

    合化局须计入：三会火局可以整个改写格局，若只数天干藏干，
    「三会成局」这条信息就等于算了不用。仅在「化神得令」时加成——
    不得令者古法多作「合而不化」，不改变五行格局。
    """
    powers = {w: 0.0 for w in ("木", "火", "土", "金", "水")}
    for pillar in bazi:
        powers[WU_XING_GAN[pillar[0]]] += 1.0
    for p in canggan_detail["四柱藏干"]:
        for h in p["藏干"]:
            powers[h["五行"]] += h["力量"]

    hua_applied = []
    if relations:
        for it in relations["关系列表"]:
            bonus = HUA_BONUS.get(it["类型"])
            if bonus and it.get("化神得令") and it.get("五行"):
                powers[it["五行"]] += bonus
                hua_applied.append(f"{it['关系']}（化神得令 +{bonus}）")
    return {k: round(v, 3) for k, v in powers.items()}, hua_applied


def determine_yongshen(bazi, canggan_detail, day_master, relations):
    """
    用神 / 喜神 / 忌神 / 仇神判定。

    **流派声明：以扶抑法为主、调候法为辅、必要时引入通关。**
    命理各家对用神取法分歧极大（扶抑/调候/通关/病药/格局），
    本函数不假装唯一正解，而是显式输出所依据的流派、依据链与置信度；
    当扶抑与调候指向冲突时，如实披露分歧而非强行给出单一答案。
    """
    day_gan = bazi[2][0]
    day_wx = WU_XING_GAN[day_gan]
    month_zhi = bazi[1][1]
    score = day_master["强弱分"]
    powers, hua_applied = _element_powers(bazi, canggan_detail, relations)

    # 以日主为中心的五行角色
    yin_wx = next(k for k, v in SHENG.items() if v == day_wx)   # 生我者 → 印
    bi_wx = day_wx                                               # 同我者 → 比劫
    shi_wx = SHENG[day_wx]                                       # 我生者 → 食伤
    cai_wx = KE[day_wx]                                          # 我克者 → 财
    guan_wx = next(k for k, v in KE.items() if v == day_wx)      # 克我者 → 官杀

    basis = [
        f"日主 {day_gan}（{day_wx}），生于{month_zhi}月，"
        f"月令司令 {canggan_detail['月令司令']['干']}"
        f"（{canggan_detail['月令司令']['十神']}）",
        f"强弱分 {score}（{day_master['标签']}），"
        f"{'得令' if day_master['得令'] else '失令'}，通根{day_master['通根质量']}",
    ]

    # ---- 扶抑法取用 ----
    # 关键：身弱不能一律「印比中取力量大者」。日主之病在哪，用神就在哪：
    #   杀重身轻 → 用印化杀（比劫敌不过官杀）
    #   财多身弱 → 用比劫劫财（印会被财所坏）
    #   食伤泄身太过 → 用印制食伤
    # 身强同理，看最需要疏导的方向，而非单纯取力量最大者。
    if score >= 56:
        # 身强宜克泄耗，取盘中已有力量者，用神方能「有力可用」
        candidates = [(guan_wx, "官杀"), (shi_wx, "食伤"), (cai_wx, "财星")]
        candidates.sort(key=lambda x: powers[x[0]], reverse=True)
        fuyi_wx, fuyi_role = candidates[0]
        # 印比同旺而无泄处时，独用官杀反易激,以食伤顺泄为宜
        if powers[yin_wx] >= 3.0 and fuyi_role == "官杀" and powers[shi_wx] >= 1.0:
            fuyi_wx, fuyi_role = shi_wx, "食伤"
            basis.append(f"印星过旺（{powers[yin_wx]}），官杀反被印化，改取食伤（{shi_wx}）顺泄")
        else:
            basis.append(
                f"身强宜抑，官杀/食伤/财三者中 {fuyi_role}（{fuyi_wx}）"
                f"在盘中力量最著（{powers[fuyi_wx]}），取为扶抑用神")
        favorable = [guan_wx, shi_wx, cai_wx]
        unfavorable = [yin_wx, bi_wx]
    elif score <= 44:
        # 身弱宜生扶，先辨「病」在官杀、在财、还是在食伤
        drains = sorted(
            [(guan_wx, "官杀"), (cai_wx, "财星"), (shi_wx, "食伤")],
            key=lambda x: powers[x[0]], reverse=True)
        top_wx, top_role = drains[0]
        if top_role == "财星" and powers[cai_wx] >= 2.5:
            fuyi_wx, fuyi_role = bi_wx, "比劫"
            basis.append(
                f"财星（{cai_wx}·{powers[cai_wx]}）为全局最重，属财多身弱。"
                f"财能坏印，故不取印而取比劫（{bi_wx}）分财帮身")
        elif top_role in ("官杀", "食伤"):
            fuyi_wx, fuyi_role = yin_wx, "印绶"
            basis.append(
                f"{top_role}（{top_wx}·{powers[top_wx]}）为全局最重，"
                f"{'杀重身轻宜化不宜抗' if top_role == '官杀' else '食伤泄身太过宜制'}，"
                f"取印（{yin_wx}）{'化杀生身' if top_role == '官杀' else '制食护身'}"
                f"，比劫（{bi_wx}）{'敌不过官杀' if top_role == '官杀' else '反助食伤'}故居次")
        elif powers[yin_wx] >= powers[bi_wx]:
            fuyi_wx, fuyi_role = yin_wx, "印绶"
            basis.append(f"身弱宜扶，印（{yin_wx}·{powers[yin_wx]}）较比劫有力，取印为用")
        else:
            fuyi_wx, fuyi_role = bi_wx, "比劫"
            basis.append(f"身弱宜扶，比劫（{bi_wx}·{powers[bi_wx]}）较印有力，取比劫为用")
        favorable = [yin_wx, bi_wx]
        unfavorable = [guan_wx, cai_wx, shi_wx]
    else:
        # 中和：扶抑无从下手，转以调候/通关为主
        fuyi_wx, fuyi_role = None, None
        favorable, unfavorable = [], []
        basis.append("强弱居中和区间（45–55），扶抑法难以定夺，转以调候与通关为主要取用依据")

    # ---- 调候 ----
    th = _tiaohou(day_gan, month_zhi)
    if th["元素"]:
        basis.append(f"调候：{th['说明']}")

    # ---- 扶抑 vs 调候 是否同向 ----
    conflict_note = None
    if fuyi_wx and th["元素"] and th["需求"] == "强":
        if th["元素"] == fuyi_wx:
            primary, primary_reason = fuyi_wx, "扶抑与调候同指一元，取用明确"
            agreement = "一致"
        elif th["元素"] in unfavorable:
            # 最典型的分歧：调候所需正是扶抑所忌
            primary, primary_reason = th["元素"], "调候优先于扶抑（气候失衡时，命局先求可活，再求平衡）"
            agreement = "冲突"
            # 既已采调候优先，该元素须从忌神移入喜神，否则喜忌自相矛盾
            unfavorable = [w for w in unfavorable if w != th["元素"]]
            favorable = [th["元素"]] + [w for w in favorable if w != th["元素"]]
            conflict_note = (
                f"扶抑法主{fuyi_wx}、调候法主{th['元素']}，二者相反。"
                f"本结论采调候优先（{month_zhi}月寒燥失衡时的通行处理），"
                f"故{th['元素']}由忌转喜；但主扶抑一派会取{fuyi_wx}而仍以{th['元素']}为忌，"
                f"请勿视为唯一定论。")
        else:
            primary, primary_reason = fuyi_wx, "扶抑定主用神，调候元素列为喜神并行"
            agreement = "部分一致"
            if th["元素"] not in favorable:
                favorable = favorable + [th["元素"]]
    elif fuyi_wx:
        primary, primary_reason, agreement = fuyi_wx, f"扶抑法取{fuyi_role}为用", "调候无需求"
    elif th["元素"]:
        primary, primary_reason, agreement = th["元素"], "中和局以调候定用神", "仅调候"
        favorable = [th["元素"], _sheng_of(th["元素"])]
        # 忌神是「克用神者」，不是「用神所克者」——方向不能反
        unfavorable = [_ke_of(th["元素"])]
    else:
        primary, primary_reason, agreement = None, "中和且无调候急需，全局无明显病处，宜顺势而为", "无"

    # ---- 通关：两强相争时的疏导之神 ----
    # 注意：通关神未必是喜神。若通关神本身属忌（如身弱而通关神为财），
    # 只作结构说明、不并入喜神，否则喜忌表会自相矛盾。
    tongguan = None
    ranked = sorted(powers.items(), key=lambda x: x[1], reverse=True)
    (w1, p1), (w2, p2) = ranked[0], ranked[1]
    if p1 >= 3.0 and p2 >= 3.0 and (KE[w1] == w2 or KE[w2] == w1) and abs(p1 - p2) < 1.5:
        mediator = SHENG[w1] if KE[w1] == w2 else SHENG[w2]
        conflicts_with_yong = mediator in unfavorable
        tongguan = {
            "元素": mediator,
            "并入喜神": not conflicts_with_yong,
            "说明": f"{w1}（{p1}）与{w2}（{p2}）势均力敌且相克，成交战之势；"
                    f"{mediator}可通关化解，转克为生"
                    + ("" if not conflicts_with_yong else
                       f"。但{mediator}相对日主属忌神，通关之利与扶抑之弊并存，"
                       f"不并入喜神，仅作命局结构说明"),
        }
        if not conflicts_with_yong and mediator not in favorable:
            favorable.append(mediator)

    # ---- 归类：喜 / 忌 / 仇 / 闲 ----
    all_wx = ["木", "火", "土", "金", "水"]
    favorable = [w for w in dict.fromkeys(favorable) if w]
    unfavorable = [w for w in dict.fromkeys(unfavorable) if w and w not in favorable]
    # 仇神：生忌神者（助纣为虐），且本身不在喜忌之列
    chou = []
    for bad in unfavorable:
        feeder = _sheng_of(bad)
        if feeder and feeder not in favorable and feeder not in unfavorable and feeder not in chou:
            chou.append(feeder)
    idle = [w for w in all_wx if w not in favorable and w not in unfavorable and w not in chou]

    # ---- 置信度 ----
    conf_score = 0.75
    conf_reasons = []
    if 45 <= score <= 55:
        conf_score -= 0.25
        conf_reasons.append("强弱处于中和临界区，扶抑取用本身争议大")
    elif score >= 70 or score <= 30:
        conf_score += 0.1
        conf_reasons.append("强弱倾向明确，扶抑方向稳定")
    if day_master["特殊格局预警"]:
        conf_score -= 0.3
        conf_reasons.append(f"存在特殊格局可能：{day_master['特殊格局预警']}")
    if agreement == "冲突":
        conf_score -= 0.2
        conf_reasons.append("扶抑与调候结论相反，取用取决于流派立场")
    elif agreement == "一致":
        conf_score += 0.1
        conf_reasons.append("扶抑与调候互相印证")
    if canggan_detail["月令司令"]["按本气估算"]:
        conf_score -= 0.05
        conf_reasons.append("人元司令按本气估算（未精确到节令日差），月令权重略有误差")
    elif not canggan_detail["月令司令"]["入藏干"]:
        conf_score -= 0.05
        conf_reasons.append(
            f"当令之气为{canggan_detail['月令司令']['干']}，不在月支藏干之内"
            f"（分野与藏干两套传承不一致），月令力量未计司令加成")
    if primary and powers.get(primary, 0) < 0.5:
        conf_score -= 0.15
        conf_reasons.append(f"用神{primary}在原局力量仅{powers.get(primary, 0)}，用神无力，须待岁运引至")
    if relations.get("冲力", 0) >= 2.5:
        # 改用加权冲力而非条目数：六冲与相破的分量差数倍，数条目会误判
        conf_score -= 0.05
        conf_reasons.append(
            f"原局刑冲之力偏重（冲力{relations['冲力']}），"
            f"五行力量易被引动改变，静态取用参考性下降")

    if not conf_reasons:
        # 绝不输出没有依据的裸置信度
        conf_reasons.append("强弱、调候、通根、刑冲各项均无异常，按标准扶抑法取用")
    conf_score = round(max(0.1, min(0.95, conf_score)), 2)
    level = "high" if conf_score >= 0.7 else ("medium" if conf_score >= 0.45 else "low")

    caveats = ["用神取法各家分歧极大（扶抑/调候/通关/病药/格局），本结论仅代表所声明流派的推断"]
    if conflict_note:
        caveats.append(conflict_note)
    if day_master["特殊格局预警"]:
        caveats.append(day_master["特殊格局预警"] + "，建议由专业命师复核")
    if level == "low":
        caveats.append("置信度偏低，叙事层应以「倾向于」「可能」等措辞表述，不得断言")

    return {
        "流派": "扶抑为主、调候为辅、必要时通关",
        "用神": primary,
        "用神十神": _shishen_of_element(day_gan, primary) if primary else None,
        "取用理由": primary_reason,
        "喜神": favorable,
        "忌神": unfavorable,
        "仇神": chou,
        "闲神": idle,
        "扶抑用神": fuyi_wx,
        "调候": th,
        "扶抑调候关系": agreement,
        "通关": tongguan,
        "五行力量": powers,
        "合化加成": hua_applied,
        "判定依据": basis,
        "置信度": {"level": level, "score": conf_score, "reasons": conf_reasons},
        "注意事项": caveats,
    }


# ============================================================
# 5. 跨系统一致性检测
# ============================================================

# 紫微主星气质分类（用于与八字日主强弱交叉验证）
ZIWEI_STRONG_STARS = {"紫微", "天府", "七杀", "破军", "贪狼", "武曲", "太阳", "廉贞"}
ZIWEI_SOFT_STARS = {"天同", "太阴", "天梁", "天相", "天机", "巨门", "文昌", "文曲"}
# 财帛宫主星的财富性质
ZIWEI_WEALTH_STABLE = {"武曲", "天府", "太阴", "禄存", "天相"}
ZIWEI_WEALTH_VOLATILE = {"破军", "七杀", "廉贞", "贪狼", "巨门"}

# 星座元素 → 对应五行倾向
ZODIAC_ELEMENT_WX = {
    "火象": {"火", "木"}, "土象": {"土", "金"},
    "风象": {"木", "金"}, "水象": {"水"},
}
ZODIAC_TO_ELEMENT = {
    "白羊座": "火象", "狮子座": "火象", "射手座": "火象",
    "金牛座": "土象", "处女座": "土象", "摩羯座": "土象",
    "双子座": "风象", "天秤座": "风象", "水瓶座": "风象",
    "巨蟹座": "水象", "天蝎座": "水象", "双鱼座": "水象",
}


def cross_validate(person, yongshen, day_master, relations):
    """
    八字 / 紫微 / 姓名 / 星座 四系统交叉验证。

    设计意图：**分歧比一致更有信息量**。
    四套系统本就来自不同源流，硬凑成一个和谐叙事是最常见的幻觉来源；
    显式标出冲突点，能让叙事层把它当作「命主内在张力」来讨论，
    而不是各说各话、互相矛盾却假装无事发生。
    """
    checks = []

    def add(cid, name, systems, verdict, detail):
        checks.append({"id": cid, "维度": name, "系统": systems,
                       "结论": verdict, "说明": detail})

    ziwei = person.get("ziwei") or {}
    ming_stars = set(ziwei.get("命宫主星") or [])
    wealth_stars = set(ziwei.get("财帛宫主星") or [])
    wuge = person.get("wuge")

    # --- 1. 性格强度：八字日主强弱 vs 紫微命宫主星 ---
    if ming_stars:
        strong_hit = ming_stars & ZIWEI_STRONG_STARS
        soft_hit = ming_stars & ZIWEI_SOFT_STARS
        bazi_strong = day_master["强弱分"] >= 56
        bazi_weak = day_master["强弱分"] <= 44
        stars_txt = "、".join(sorted(ming_stars))
        if strong_hit and bazi_strong:
            add("personality", "性格强度", ["八字", "紫微"], "一致",
                f"八字{day_master['标签']}（{day_master['强弱分']}）"
                f"与命宫强势星「{'、'.join(sorted(strong_hit))}」互相印证，主体性强、推进力足")
        elif soft_hit and bazi_weak and not strong_hit:
            add("personality", "性格强度", ["八字", "紫微"], "一致",
                f"八字{day_master['标签']}与命宫柔性星「{'、'.join(sorted(soft_hit))}」一致，"
                f"偏协调型人格，借力优于硬撑")
        elif strong_hit and bazi_weak:
            add("personality", "性格强度", ["八字", "紫微"], "分歧",
                f"八字{day_master['标签']}（{day_master['强弱分']}），但命宫见「{stars_txt}」等强势星。"
                f"典型的「心气高于体量」结构：企图心与实际承载力不匹配，"
                f"易出现眼高手低或长期透支，是值得重点展开的内在张力")
        elif soft_hit and bazi_strong:
            add("personality", "性格强度", ["八字", "紫微"], "分歧",
                f"八字{day_master['标签']}但命宫见「{stars_txt}」等柔性星，"
                f"外柔内刚：对外温和退让，内在主意极大，压力多来自不表达")
        else:
            add("personality", "性格强度", ["八字", "紫微"], "不确定",
                f"命宫主星「{stars_txt}」气质中性，与八字{day_master['标签']}无明显印证或冲突")

    # --- 2. 财富结构：八字财星力量 vs 紫微财帛宫 ---
    if wealth_stars:
        day_wx = WU_XING_GAN[person["bazi"][2][0]]
        cai_wx = KE[day_wx]
        cai_power = yongshen["五行力量"].get(cai_wx, 0)
        cai_strong = cai_power >= 2.5
        cai_weak = cai_power < 1.0
        stable = wealth_stars & ZIWEI_WEALTH_STABLE
        volatile = wealth_stars & ZIWEI_WEALTH_VOLATILE
        stars_txt = "、".join(sorted(wealth_stars))
        cai_is_yong = cai_wx in ([yongshen["用神"]] if yongshen["用神"] else []) or cai_wx in yongshen["喜神"]
        if cai_strong and stable:
            add("wealth", "财富结构", ["八字", "紫微"], "一致",
                f"八字财星（{cai_wx}）力量{cai_power}偏旺，财帛宫见「{stars_txt}」，"
                f"两系统同指稳健积累型财路")
        elif cai_weak and volatile:
            add("wealth", "财富结构", ["八字", "紫微"], "一致",
                f"八字财星（{cai_wx}）仅{cai_power}偏弱，财帛宫见「{stars_txt}」，"
                f"同指财来财去、宜守不宜搏")
        elif cai_strong and volatile:
            add("wealth", "财富结构", ["八字", "紫微"], "分歧",
                f"八字财星力量{cai_power}充沛，但财帛宫见「{stars_txt}」等动荡星。"
                f"多主赚取能力强而留存能力弱，格局大但波动剧烈，"
                f"关键变量在于是否有制约机制而非赚取能力")
        elif cai_weak and stable:
            add("wealth", "财富结构", ["八字", "紫微"], "分歧",
                f"八字财星仅{cai_power}偏弱，财帛宫却见「{stars_txt}」等稳定星。"
                f"多主守成有余、开拓不足，财富来自积累与职务性收入而非机会")
        else:
            add("wealth", "财富结构", ["八字", "紫微"], "不确定",
                f"八字财星力量{cai_power}、财帛宫「{stars_txt}」，两者指向均不鲜明")
        if cai_is_yong and cai_weak:
            add("wealth_yong", "财为用而无力", ["八字"], "提示",
                f"财（{cai_wx}）既是用神/喜神又力量薄弱（{cai_power}），"
                f"主求财意愿强于实际条件，须待岁运补足方能兑现")

    # --- 3. 姓名补益：用神五行 vs 姓名人格/总格五行（最具实用价值的一条）---
    if wuge and yongshen["用神"]:
        wg = wuge.get("五格", {})
        ren_wx = (wg.get("人格") or {}).get("五行")
        zong_wx = (wg.get("总格") or {}).get("五行")
        name_wx = {w for w in (ren_wx, zong_wx) if w}
        yong = yongshen["用神"]
        hits = name_wx & (set(yongshen["喜神"]) | {yong})
        harms = name_wx & set(yongshen["忌神"])
        conf = yongshen["置信度"]["level"]
        if yong in name_wx:
            add("name_remedy", "姓名补益", ["八字", "姓名"], "一致",
                f"用神为{yong}，姓名人格/总格五行（{ren_wx}/{zong_wx}）正落用神，"
                f"姓名与命局同向，属加成结构")
        elif hits:
            add("name_remedy", "姓名补益", ["八字", "姓名"], "部分一致",
                f"用神为{yong}，姓名五行（{ren_wx}/{zong_wx}）虽未正中用神，"
                f"但落在喜神{'、'.join(sorted(hits))}上，仍属助益")
        elif harms:
            add("name_remedy", "姓名补益", ["八字", "姓名"], "分歧",
                f"用神为{yong}，而姓名人格/总格五行（{ren_wx}/{zong_wx}）落在忌神"
                f"{'、'.join(sorted(harms))}上，姓名与命局取用方向相左"
                f"（用神置信度 {conf}，若为 low 则此结论同样不宜过度采信）")
        else:
            add("name_remedy", "姓名补益", ["八字", "姓名"], "不确定",
                f"姓名五行（{ren_wx}/{zong_wx}）既非喜亦非忌，对命局取用影响中性")

    # --- 4. 五行缺失 vs 姓名补足 ---
    # 关键：缺失是否需补，取决于该五行是喜是忌。缺忌神是好事，
    # 一律判「未补足 = 分歧」会把好事说成坏事。
    missing = person.get("missing_wx") or []
    if wuge and missing:
        wg = wuge.get("五格", {})
        name_all = {(wg.get(k) or {}).get("五行") for k in ("天格", "人格", "地格", "外格", "总格")}
        name_all.discard(None)
        want = [w for w in missing if w in set(yongshen["喜神"])]
        dont_want = [w for w in missing if w in set(yongshen["忌神"])]
        filled_want = set(want) & name_all
        filled_bad = set(dont_want) & name_all
        if want and filled_want:
            add("missing_fill", "五行缺失补足", ["八字", "姓名"], "一致",
                f"原局缺{'、'.join(want)}且正属喜用，姓名五格含{'、'.join(sorted(filled_want))}，"
                f"恰成补足，是姓名与命局最实在的一处契合")
        elif want and not filled_want:
            add("missing_fill", "五行缺失补足", ["八字", "姓名"], "分歧",
                f"原局缺{'、'.join(want)}且正属喜用，"
                f"而姓名五格（{'、'.join(sorted(name_all)) or '无'}）未涉及，该缺口未获补足")
        elif dont_want and filled_bad:
            add("missing_fill", "五行缺失补足", ["八字", "姓名"], "分歧",
                f"原局缺{'、'.join(dont_want)}本属忌神，缺反为吉；"
                f"但姓名五格补入了{'、'.join(sorted(filled_bad))}，等于把忌神请回来，方向相反")
        elif dont_want:
            add("missing_fill", "五行缺失补足", ["八字", "姓名"], "一致",
                f"原局缺{'、'.join(dont_want)}，而该五行正属忌神，"
                f"缺之反吉；姓名亦未补入，无须视为缺陷")
        else:
            add("missing_fill", "五行缺失补足", ["八字", "姓名"], "不确定",
                f"原局缺{'、'.join(missing)}，该五行于本命非喜非忌（闲神），补与不补影响有限")

    # --- 5. 星座元素 vs 日主五行倾向 ---
    zodiac = person.get("zodiac")
    if zodiac:
        elem = ZODIAC_TO_ELEMENT.get(zodiac)
        day_wx = WU_XING_GAN[person["bazi"][2][0]]
        if elem:
            expect = ZODIAC_ELEMENT_WX.get(elem, set())
            if day_wx in expect:
                add("temperament", "外显气质", ["八字", "星座"], "一致",
                    f"太阳{zodiac}（{elem}）与日主{day_wx}气质同向，内在与外显表现一致，"
                    f"他人对其印象与其自我认知偏差小")
            else:
                add("temperament", "外显气质", ["八字", "星座"], "分歧",
                    f"太阳{zodiac}（{elem}）与日主{day_wx}气质不同向。"
                    f"多主社会形象与内在驱动不一致，他人眼中的他与他眼中的自己有落差——"
                    f"这种落差本身往往是其消耗感的来源"
                    f"（按：西洋四象与五行分属不同体系，其对应关系并无定说，"
                    f"本条为四项检测中依据最弱者，宜作旁证而非主证）")

    # --- 汇总 ---
    # 统计用 Counter 泛化，避免新增结论类型（如「提示」）被静默漏计；
    # 但一致度只在四种「一致性判定」上计算——「提示」是补充说明，不参与分母。
    tally = Counter(c["结论"] for c in checks)
    n_cons = sum(1 for c in checks if c["结论"] == "一致")
    n_part = sum(1 for c in checks if c["结论"] == "部分一致")
    n_div = sum(1 for c in checks if c["结论"] == "分歧")
    n_valid = n_cons + n_part + n_div
    consistency = round((n_cons + 0.5 * n_part) / n_valid * 100, 1) if n_valid else None

    divergences = [c for c in checks if c["结论"] == "分歧"]
    if consistency is None:
        hint = "可比对的维度不足（缺姓名或出生城市等），跨系统验证未能展开"
    elif consistency >= 75:
        hint = ("各系统高度一致，可放心给出较确定的整体判断；"
                "但正因一致，更应避免同一结论在不同章节重复陈述")
    elif consistency >= 40:
        hint = ("系统间部分一致、部分冲突。**冲突项才是解读重点**——"
                "应把它们表述为命主自身的内在张力，而非四套系统互相矛盾")
    else:
        hint = ("系统间分歧显著。切勿强行调和成单一叙事，"
                "应明确指出该命造具有多面性，不同侧面在不同情境下主导")

    return {
        "一致度": consistency,
        "统计": dict(tally),
        "检测项": checks,
        "分歧焦点": [{"维度": d["维度"], "说明": d["说明"]} for d in divergences],
        "叙事指引": hint,
    }


# ============================================================
# 统一入口
# ============================================================

def build_deep_analysis(person, days_into_month=None, gender=None,
                        since_jieling=None, to_next_jieling=None,
                        now_year=None, year_ganzhi_fn=None):
    """
    在 analyze_person 结果之上追加深层分析。

    返回结构挂载于 person["deep"]，仅供叙事层加深理解，
    **不对应任何新增报告章节**（见 SKILL.md §输出纪律）。
    """
    bazi = person["bazi"]
    day_gan = bazi[2][0]

    canggan_detail = analyze_canggan_shishen(bazi, day_gan, days_into_month)
    relations = analyze_zhi_relations(bazi)
    day_master = analyze_day_master(bazi, canggan_detail, relations)
    yongshen = determine_yongshen(bazi, canggan_detail, day_master, relations)
    cross = cross_validate(person, yongshen, day_master, relations)

    # 大运流年：需要性别与节令距离，缺任一项则整块略去而非给出错值。
    dayun = None
    if gender and (since_jieling is not None or to_next_jieling is not None):
        dayun = build_dayun_timeline(
            person, gender,
            now_year or _dt.date.today().year,
            since_jieling=since_jieling, to_next_jieling=to_next_jieling,
            yongshen=yongshen, year_ganzhi_fn=year_ganzhi_fn)

    return {
        "canggan_shishen": canggan_detail,
        "zhi_relations": relations,
        "day_master": day_master,
        "yongshen": yongshen,
        "cross_validation": cross,
        "dayun": dayun,
    }


# ============================================================
# 6. 大运流年时间轴（只输出当前大运 + 未来三年）
# ============================================================
#
# 刻意不铺全表：八步大运八十年的干支表是查表信息，不是解读。
# 与命主此刻真正相关的只有「现在这十年」和「接下来三年」，
# 其余全部丢弃，以此换取对这四个时间单元的深度分析。

JIA_ZI = [g + z for g, z in zip(
    [TIAN_GAN[i % 10] for i in range(60)],
    [DI_ZHI[i % 12] for i in range(60)])]


def _ganzhi_offset(gz, n):
    """六十甲子中相对偏移 n 位（可负）。"""
    return JIA_ZI[(JIA_ZI.index(gz) + n) % 60]


def _qi_yun(bazi, gender, since_jieling, to_next_jieling):
    """
    起运推算。

    阳年男 / 阴年女顺行，数至下一节令；阴年男 / 阳年女逆行，数至上一节令。
    折算古法：三日折一年，一日折四月，一时辰（两小时）折十日。
    """
    forward = (YIN_YANG_GAN[bazi[0][0]] == "阳") == (gender == "男")
    span = to_next_jieling if forward else since_jieling
    if span is None:
        return None
    years, rem = divmod(span, 3.0)
    months, rem_d = divmod(rem * 4.0, 1.0)      # 每余 1 日 = 4 个月
    days = rem_d * 30.0                          # 不足一月者折日
    return {
        "顺逆": "顺行" if forward else "逆行",
        "顺行": forward,
        "节令距离": round(span, 3),
        "起运岁": int(years),
        "起运月": int(months),
        "起运日": int(round(days)),
        "起运年龄": round(years + months / 12.0 + days / 365.0, 2),
        "折算说明": (
            f"{'阳' if YIN_YANG_GAN[bazi[0][0]] == '阳' else '阴'}年"
            f"{gender}命{'顺' if forward else '逆'}行，"
            f"生时距{'下' if forward else '上'}一节令 {span:.2f} 日，"
            f"三日折一年，得 {int(years)} 岁 {int(months)} 个月起运"),
    }


def _pillar_shishen(day_gan, gz):
    """一柱干支相对日主的十神画像（天干 + 地支本气）。"""
    return {
        "干": gz[0],
        "支": gz[1],
        "天干十神": get_shishen(day_gan, gz[0]),
        "地支本气": CANG_GAN[gz[1]][0],
        "地支十神": get_shishen(day_gan, CANG_GAN[gz[1]][0]),
        "干五行": WU_XING_GAN[gz[0]],
        "支五行": WU_XING_GAN[CANG_GAN[gz[1]][0]],
    }


def _xi_ji_score(pic, yongshen):
    """
    喜忌倾向量化。天干主外显事象计 0.4，地支主根基实质计 0.6。
    返回 (分值 -1..1, 文字判语)。
    """
    xi, ji = set(yongshen["喜神"]), set(yongshen["忌神"])
    score = 0.0
    for wx, w in ((pic["干五行"], 0.4), (pic["支五行"], 0.6)):
        if wx in xi:
            score += w
        elif wx in ji:
            score -= w
    score = round(score, 2)
    if score >= 0.6:
        verdict = "顺境"
    elif score >= 0.2:
        verdict = "偏顺"
    elif score > -0.2:
        verdict = "参半"
    elif score > -0.6:
        verdict = "偏逆"
    else:
        verdict = "逆境"
    return score, verdict


def _zhi_interactions(zhi, targets):
    """
    某支与一组（标签, 支）的刑冲合会关系，复用原局同一套判定。

    巳申、寅巳一类既合又刑者不能只取其一——「合中带刑」与单纯的合
    是完全不同的事象，故合冲类与刑害破类分别判定后并列输出。
    """
    out = []
    for label, tz in targets:
        if not tz:
            continue
        pair = frozenset((zhi, tz))
        if zhi == tz:
            if zhi in ZI_XING:
                out.append(f"与{label}{tz}自刑")
            continue
        main = None
        if pair in LIU_CHONG:
            main = f"冲{label}{tz}"
        elif pair in LIU_HE:
            main = f"合{label}{tz}"
        elif any(pair <= set(g) and _sanhe_half(zhi, tz, g) for g in SAN_HE_GROUPS):
            main = f"与{label}{tz}半合"
        sub = None
        if pair in XIANG_XING:
            sub = f"刑{label}{tz}"
        elif pair in XIANG_HAI:
            sub = f"害{label}{tz}"
        elif pair in XIANG_PO:
            sub = f"破{label}{tz}"
        if main and sub:
            out.append(f"{main}（合中带刑，{sub[0]}）" if "合" in main
                       else f"{main}兼{sub[0]}")
        elif main:
            out.append(main)
        elif sub:
            out.append(sub)
    return out


def _sanhe_half(a, b, group):
    """三合局中含旺支（中神）者方为半合，两旁支相遇不作合论。"""
    return group[1] in (a, b)


# 十神在「运」这个层面上的事象侧重，与本命静态含义不同：
# 本命看禀赋，行运看这十年被什么力量推动。
SHISHEN_YUN_THEME = {
    "比肩": "同侪、合伙与自立",   "劫财": "竞争、破财与人情消耗",
    "食神": "输出、专业深耕与享受", "伤官": "才华外露、越界与旧秩序松动",
    "正财": "稳定收入与务实经营", "偏财": "机会财、外缘与流动性",
    "正官": "职位、规范与责任加身", "七杀": "压力、竞争位与被迫成长",
    "正印": "扶持、学习与身份认证", "偏印": "偏门技艺、独处与内向消化",
}


# 十神所属大类，用于判断干支两股力量是否真的相左。
# 同类者不必强说「内外不一」——那是句填充话，不是观察。
SHISHEN_CAMP = {
    "比肩": "自我", "劫财": "自我", "食神": "输出", "伤官": "输出",
    "正财": "取用", "偏财": "取用", "正官": "受制", "七杀": "受制",
    "正印": "受养", "偏印": "受养",
}
CAMP_OPPOSED = {frozenset(("受养", "取用")), frozenset(("输出", "受制")),
                frozenset(("自我", "受制")), frozenset(("受养", "输出"))}

DONG_VERB = {"冲": "正面撞开", "刑": "内里磨损", "害": "暗处折损", "破": "小幅剥落"}


def _unit_reading(pic, yongshen, role, seen):
    """
    把十神 / 喜忌 / 刑冲合成一句有因果链的判语。

    不写「吉」「凶」——那是结论不是解读；写清楚**什么力量在推动、
    这股力量于本命是助是耗、从哪里落地**。

    `seen` 跨单元累积已用过的论断：同一句忌神判语在四个时间单元里
    原样复读四遍，是堆料不是深度，故第二次起只留短提示。
    """
    gan_ss, zhi_ss = pic["天干十神"], pic["地支十神"]
    theme_g = SHISHEN_YUN_THEME.get(gan_ss, "")
    theme_z = SHISHEN_YUN_THEME.get(zhi_ss, "")
    yong = yongshen["用神"] if yongshen else None
    ji = set(yongshen["忌神"]) if yongshen else set()
    parts = []

    camps = frozenset((SHISHEN_CAMP.get(gan_ss, ""), SHISHEN_CAMP.get(zhi_ss, "")))
    if gan_ss == zhi_ss:
        parts.append(f"{role}{pic['干支']}干支同气，{theme_g}一事上下贯通，力度集中而无退路")
    elif camps in CAMP_OPPOSED:
        parts.append(f"{role}{pic['干支']}天干{gan_ss}主{theme_g}，地支{zhi_ss}主{theme_z}，"
                     f"两股力量方向相左，外面在做的事与内里被消耗的事并不是同一件")
    else:
        parts.append(f"{role}{pic['干支']}以{gan_ss}{theme_g}为面，{zhi_ss}{theme_z}为里")

    # —— 喜忌落点，重复者只留短提示 ——
    if yong and pic["支五行"] == yong:
        k = "支落用神"
        parts.append(f"地支正落用神{yong}，是本命最缺的那口气，借力最省"
                     if k not in seen else f"地支同落用神{yong}")
        seen.add(k)
    elif yong and pic["干五行"] == yong:
        k = "干透用神"
        parts.append(f"天干透用神{yong}，助力可见却无根，须外求方能落地"
                     if k not in seen else f"用神{yong}仍只透于天干")
        seen.add(k)
    elif pic["支五行"] in ji:
        k = f"支坐忌{pic['支五行']}"
        parts.append(f"地支坐忌神{pic['支五行']}，根基处即是消耗处，"
                     f"顺逆不取决于用力多寡，而取决于是否踩在忌神上"
                     if "支坐忌" not in {x[:3] for x in seen}
                     else f"地支复坐忌神{pic['支五行']}，同一处消耗延续")
        seen.add(k)

    # —— 引动原局，措辞须与实际关系相符 ——
    if pic["与原局"]:
        dong = [x for x in pic["与原局"] if x[0] in DONG_VERB or "自刑" in x]
        he = [x for x in pic["与原局"] if x not in dong]
        if dong:
            v = ("自我磨耗于" if "自刑" in dong[0]
                 else DONG_VERB.get(dong[0][0], "扰动"))
            k = "引动"
            parts.append(f"引动原局：{'、'.join(dong)}，{v}所临之柱，此期变动多由此起"
                         if k not in seen else f"再度{'、'.join(dong)}")
            seen.add(k)
        if he and not dong:
            parts.append(f"{'、'.join(he)}，合则牵绊，事缓而黏")
    return "；".join(parts) + "。"


def build_dayun_timeline(person, gender, now_year, now_month=6,
                         since_jieling=None, to_next_jieling=None,
                         yongshen=None, year_ganzhi_fn=None):
    """
    大运流年时间轴：**只输出当前所行大运与未来三个流年**。

    有意不铺八步大运全表——那是查表信息不是解读。
    篇幅省下来用于四个时间单元各自的十神、喜忌与刑冲合会分析。
    """
    bazi = person["bazi"]
    day_gan = bazi[2][0]
    birth_year = person.get("_birth_year") or now_year

    qi = _qi_yun(bazi, gender, since_jieling, to_next_jieling)
    if qi is None:
        return {"可用": False, "原因": "节令时刻不可得，起运数无法推算"}

    step = 1 if qi["顺行"] else -1
    age = now_year - birth_year          # 周岁近似，误差不超过一年
    idx = int((age - qi["起运年龄"]) // 10)

    targets = [(PILLAR_NAMES[i] + "支", p[1]) for i, p in enumerate(bazi)]

    seen = set()

    def unit(gz, role="此运"):
        pic = _pillar_shishen(day_gan, gz)
        sc, verdict = (_xi_ji_score(pic, yongshen) if yongshen else (0.0, "未判"))
        pic.update({"干支": gz, "喜忌分": sc, "喜忌": verdict,
                    "与原局": _zhi_interactions(gz[1], targets)})
        pic["解读"] = _unit_reading(pic, yongshen, role, seen)
        for k in ("干", "支"):          # 与「干支」重复，去掉以免叙事层照抄字段
            pic.pop(k, None)
        pic["_zhi"] = gz[1]
        return pic

    if idx < 0:
        # 尚未交运者行的是月柱余气，不能假装已在某步大运上。
        dayun = unit(bazi[1], "月柱余气")
        dayun.update({
            "状态": "未起运",
            "第几步": 0,
            "说明": f"{qi['起运岁']}岁{qi['起运月']}个月方交首运，"
                    f"现行月柱 {bazi[1]} 之余气，本命格局尚未展开，"
                    f"此期表现多随家庭环境而非自身命局",
        })
    else:
        gz = _ganzhi_offset(bazi[1], step * (idx + 1))
        start_age = round(qi["起运年龄"] + idx * 10, 2)
        dayun = unit(gz, "本运")
        dayun.update({
            "状态": "行运中",
            "第几步": idx + 1,
            "起始年龄": start_age,
            "结束年龄": round(start_age + 10, 2),
            "起止公历": f"{birth_year + int(start_age)}—{birth_year + int(start_age) + 10}",
            "已行年数": round(age - start_age, 1),
        })

    liunian = []
    for y in range(now_year, now_year + 3):
        gz = year_ganzhi_fn(y) if year_ganzhi_fn else _ganzhi_offset(bazi[0], y - birth_year)
        u = unit(gz, f"{y}年")
        u["年份"] = y
        u["虚岁"] = y - birth_year + 1
        u["与大运"] = _zhi_interactions(gz[1], [("大运支", dayun["_zhi"])])
        liunian.append(u)

    # 三年中挑出最值得说的一年：优先取与大运或原局有冲刑者（变动明确），
    # 其次取喜忌绝对值最大者（力度明确）。平铺三年等于没有重点。
    def _salience(u):
        hits = u["与原局"] + u["与大运"]
        chong = sum(1 for x in hits if x[0] in "冲刑")
        return (chong, abs(u["喜忌分"]))
    key_year = max(liunian, key=_salience) if liunian else None
    focus = None
    if key_year:
        why = ([x for x in key_year["与原局"] + key_year["与大运"] if x[0] in "冲刑"]
               or [f"{key_year['喜忌']}（{key_year['喜忌分']:+}）"])
        focus = (f"{key_year['年份']}年（{key_year['干支']}）是三年中变量最大的一年："
                 f"{'、'.join(why)}。此年的关键不在结果好坏，"
                 f"而在它会把{dayun['干支']}这十年的主题提前逼到台面上")

    for u in liunian:
        u.pop("_zhi", None)
    dayun.pop("_zhi", None)

    return {
        "可用": True,
        "起运": qi,
        "当前大运": dayun,
        "未来三年": liunian,
        "三年焦点": focus,
        "范围说明": "仅取当前大运与未来三个流年；八步大运全表属查表信息，故不输出",
    }
