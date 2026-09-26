"""템플릿 고르기 — 주문서에 가장 덜 안 맞는 것을 고른다.

점수만 내고 끝내지 않는다. 왜 그것을 골랐고 무엇이 모자란지 함께 적는다.
견적서와 고객 설명에 그대로 쓰기 때문이다.
"""

from __future__ import annotations

from .models import Brief, MatchScore, TemplateSpec

PAGE_MATCH = 50.0
PAGE_MISS = 34.0
INDUSTRY_HIT = 18.0
INDUSTRY_GENERAL = 6.0
MOOD_HIT = 6.0
MOOD_CAP = 18.0
FEATURE_WEIGHT = 22.0
GOAL_HIT = 4.0
GOAL_CAP = 12.0


def score_template(brief: Brief, template: TemplateSpec) -> MatchScore:
    score = 0.0
    reasons: list[str] = []
    penalties: list[str] = []

    # 1. 쪽수 — 고객이 산 물건이 몇 쪽인가. 가장 무겁다.
    if brief.site.pages == template.page_count:
        score += PAGE_MATCH
        reasons.append(f"요청한 {brief.site.pages}쪽 구성과 일치")
    else:
        score -= PAGE_MISS
        penalties.append(f"{template.page_count}쪽 템플릿인데 {brief.site.pages}쪽을 요청")

    # 2. 업종
    industry = brief.business.industry
    if industry in template.industries:
        score += INDUSTRY_HIT
        reasons.append(f"{industry} 업종을 위해 만든 템플릿")
    elif "general" in template.industries:
        score += INDUSTRY_GENERAL
        reasons.append("업종 제한이 없는 범용 템플릿")
    else:
        penalties.append(f"{industry} 업종은 상정하지 않은 템플릿")

    # 3. 분위기
    shared_moods = [m for m in brief.brand.mood if m in template.moods]
    if shared_moods:
        gained = min(MOOD_CAP, MOOD_HIT * len(shared_moods))
        score += gained
        reasons.append("분위기가 겹침: " + ", ".join(shared_moods))

    # 4. 기능 — 요청한 것 중 몇 개를 담을 수 있나.
    wanted = brief.site.features
    if wanted:
        covered = [f for f in wanted if f in template.features]
        missing = [f for f in wanted if f not in template.features]
        ratio = len(covered) / len(wanted)
        score += FEATURE_WEIGHT * ratio
        if covered:
            reasons.append(f"요청 기능 {len(covered)}/{len(wanted)}개 수용: " + ", ".join(covered))
        if missing:
            penalties.append("담을 수 없는 기능: " + ", ".join(missing))
    else:
        score += FEATURE_WEIGHT * 0.5

    # 5. 목표
    shared_goals = [g for g in brief.site.goals if g in template.goals]
    if shared_goals:
        gained = min(GOAL_CAP, GOAL_HIT * len(shared_goals))
        score += gained
        reasons.append("목표가 맞음: " + ", ".join(shared_goals))

    return MatchScore(template=template, score=round(score, 2), reasons=reasons, penalties=penalties)


def rank(brief: Brief, templates: list[TemplateSpec]) -> list[MatchScore]:
    """점수 높은 순. 같으면 템플릿 id 순으로 늘 같은 답이 나오게 한다."""
    if not templates:
        raise ValueError("고를 템플릿이 없습니다")
    scored = [score_template(brief, t) for t in templates]
    return sorted(scored, key=lambda m: (-m.score, m.template.id))


def choose(brief: Brief, templates: list[TemplateSpec]) -> MatchScore:
    best = rank(brief, templates)[0]
    if best.score <= 0:
        best.penalties.append("맞는 템플릿이 없어 가장 덜 어긋난 것을 골랐습니다 — 사람이 볼 것")
    return best
