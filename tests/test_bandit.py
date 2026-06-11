"""Sprint 4 gate: bandit sim — convergence, exploration floor, no noise-kills."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bandit import (  # noqa: E402
    FLOOR_CLICKS,
    FLOOR_CONVERSIONS,
    Arm,
    BanditState,
)


def _state(arms):
    st = BanditState()
    for a in arms:
        st.add_arm(a)
    return st


def test_arm_update_math():
    a = Arm("o1:c1")
    a.record(clicks=100, conversions=3, decay=1.0)
    assert a.alpha == 4.0 and a.beta == 98.0
    assert a.clicks == 100 and a.conversions == 3


def test_update_rejects_impossible_counts():
    a = Arm("o1:c1")
    try:
        a.record(clicks=2, conversions=5)
        assert False
    except ValueError:
        pass


def test_no_kill_below_exploration_floor():
    a = Arm("o1:c1", views=2000, revenue=0.50)
    a.record(clicks=int(FLOOR_CLICKS * 0.5), conversions=0, decay=1.0)
    st = _state([a])
    assert st.evaluate_kills() == []
    assert not a.killed


def test_kill_after_floor_with_bad_rpm():
    a = Arm("o1:c1", views=50000, revenue=10.0, refund_rate=0.10)
    a.record(clicks=FLOOR_CLICKS, conversions=2, decay=1.0)
    st = _state([a])
    assert st.evaluate_kills() == ["o1:c1"] and a.killed


def test_conversion_floor_alone_triggers_eligibility():
    a = Arm("o1:c1", views=100000, revenue=20.0)
    a.record(clicks=500, conversions=FLOOR_CONVERSIONS, decay=1.0)
    assert a.past_floor


def test_good_rpm_survives_after_floor():
    a = Arm("o1:c1", views=10000, revenue=400.0, refund_rate=0.05)
    a.record(clicks=FLOOR_CLICKS, conversions=40, decay=1.0)
    st = _state([a])
    assert st.evaluate_kills() == [] and not a.killed


def test_hard_kill_bypasses_floor():
    a = Arm("o1:c1")
    st = _state([a])
    st.hard_kill("o1:c1", reason="refund>15%")
    assert a.killed


def test_allocation_sums_to_one_and_excludes_killed():
    a1, a2, a3 = Arm("a"), Arm("b"), Arm("dead", killed=True)
    st = _state([a1, a2, a3])
    w = st.allocate(seed=7)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert "dead" not in w and set(w) == {"a", "b"}


def test_convergence_to_better_arm():
    """Simulate: arm A converts at 2%, arm B at 0.5%. After realistic traffic,
    A must receive the dominant allocation share."""
    rng = random.Random(42)
    a = Arm("A", commission_per_conversion=30.0)
    b = Arm("B", commission_per_conversion=30.0)
    st = _state([a, b])
    for _ in range(40):
        ca = sum(1 for _ in range(100) if rng.random() < 0.02)
        cb = sum(1 for _ in range(100) if rng.random() < 0.005)
        a.record(clicks=100, conversions=ca, decay=1.0)
        b.record(clicks=100, conversions=cb, decay=1.0)
    w = st.allocate(seed=99)
    # Allocation is value-proportional (not winner-take-all): with true rates
    # 2% vs 0.5% the theoretical share is ~0.8; realized sim rates put it ~0.73.
    assert w["A"] > 0.70 and w["A"] > 2 * w["B"], f"expected A dominant, got {w}"


def test_new_arm_gets_exploration_share():
    veteran = Arm("vet", commission_per_conversion=30.0)
    veteran.record(clicks=5000, conversions=75, decay=1.0)
    rookie = Arm("new", commission_per_conversion=30.0)
    st = _state([veteran, rookie])
    w = st.allocate(seed=3)
    assert w["new"] > 0.05, f"rookie starved: {w}"


def test_cadence_plan_respects_total_and_floor():
    a = Arm("A", commission_per_conversion=30.0)
    a.record(clicks=1000, conversions=25, decay=1.0)
    b = Arm("B", commission_per_conversion=30.0)
    st = _state([a, b])
    plan = st.cadence_plan(posts_per_day=3, seed=11)
    assert sum(plan.values()) >= 1 and sum(plan.values()) <= 4
    assert all(v >= 0 for v in plan.values())


def test_state_roundtrip_rows():
    a = Arm("o1:c1", commission_per_conversion=20.0)
    a.record(clicks=100, conversions=5, decay=1.0)
    rows = _state([a]).to_rows()
    st2 = BanditState.from_rows(rows)
    arm = st2.arms["o1:c1"]
    assert arm.alpha == 6.0 and arm.beta == 96.0 and arm.clicks == 100
