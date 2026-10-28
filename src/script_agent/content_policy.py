"""Conservative visual choices when the catalog contains text facts, not UI assets."""

POLICY_ID = "grounded-creative-v1"
NEUTRAL_TITLES = ("把想法放进画面", "开始你的下一条视频", "让画面和文字一起讲述")
NEUTRAL_VISUALS = (
    "创作者面对镜头，提出本条视频的主题。",
    "桌面上的纸质分镜卡依次展开。",
    "创作者面向镜头，画面留白承接旁白。",
    "界面占位镜头：等待真实产品截图或录屏，当前仅呈现本镜旁白文字卡。",
)
FACT_VISUAL_PREFIX = "展示素材原文文字卡："


def fact_visual(fact):
    return FACT_VISUAL_PREFIX + fact["text"]


def creative_options(facts):
    return {
        "policy_id": POLICY_ID,
        "titles": list(NEUTRAL_TITLES),
        "neutral_visuals": list(NEUTRAL_VISUALS),
        "fact_visuals": [{"fact_id": fact["id"], "quote": fact["text"], "visual": fact_visual(fact)} for fact in facts.values()],
    }


def policy_snapshot():
    return {"policy_id": POLICY_ID, "titles": NEUTRAL_TITLES, "neutral_visuals": NEUTRAL_VISUALS, "fact_visual_prefix": FACT_VISUAL_PREFIX}
