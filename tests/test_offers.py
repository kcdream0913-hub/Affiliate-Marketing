"""Sprint 2 gate: feed parser vs fixture + rubric scorer kill/rank assertions."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.offers import (  # noqa: E402
    FeedUnavailable,
    OfferInput,
    parse_feed_xml,
    rank_candidates,
    score_offer,
)

FEED_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<Catalog>
  <Category>
    <Name>Health &amp; Fitness</Name>
    <Category>
      <Name>Sleep</Name>
      <Site>
        <Id>SLEEPWELL</Id>
        <Title>Sleep Well Program</Title>
        <Gravity>42.5</Gravity>
        <AverageEarningsPerSale>87.20</AverageEarningsPerSale>
        <InitialEarningsPerSale>45.10</InitialEarningsPerSale>
        <PercentPerSale>70</PercentPerSale>
        <PercentPerRebill>40</PercentPerRebill>
        <HasRecurringProducts>true</HasRecurringProducts>
        <ActivateDate>2024-03-01</ActivateDate>
      </Site>
    </Category>
  </Category>
  <Category>
    <Name>Home &amp; Garden</Name>
    <Site>
      <Id>ORGANIZE1</Id>
      <Title>Home Organizer Blueprint</Title>
      <Gravity>3.2</Gravity>
      <AverageEarningsPerSale>22.00</AverageEarningsPerSale>
      <PercentPerSale>75</PercentPerSale>
      <HasRecurringProducts>false</HasRecurringProducts>
    </Site>
  </Category>
</Catalog>
"""


def test_feed_parses_nested_categories():
    listings = parse_feed_xml(FEED_FIXTURE)
    assert len(listings) == 2
    sw = next(l for l in listings if l.external_id == "SLEEPWELL")
    assert sw.category == "Health & Fitness > Sleep"
    assert sw.gravity == 42.5 and sw.avg_dollar_per_sale == 87.20
    assert sw.has_recurring and sw.percent_per_rebill == 40


def test_feed_offer_row_provenance():
    row = parse_feed_xml(FEED_FIXTURE)[0].to_offer_row()
    assert row["network"] == "clickbank" and row["status"] == "candidate"
    assert row["source"]["gravity"] == "feed" and row["source"]["cookie_days"] == "manual"
    assert row["cookie_days"] == 60


def test_feed_unparseable_raises():
    try:
        parse_feed_xml("<html>moved</html>")
        assert False
    except FeedUnavailable:
        pass


def test_feed_schema_drift_raises():
    try:
        parse_feed_xml("<Catalog><Category><Name>Empty</Name></Category></Catalog>")
        assert False
    except FeedUnavailable:
        pass


# --- scorer -------------------------------------------------------------------
def _good_offer(**kw):
    base = dict(
        name="Good", network="clickbank", epc=1.20, refund_rate=0.04,
        commission_per_conversion=45.0, demo_coherence=0.8, demand_velocity=0.6,
        payout_reliability=0.9, gravity=42.0, cookie_days=60, payout_terms="NET15",
        provenance={"epc": "feed", "refund_rate": "scrape"},
    )
    base.update(kw)
    return OfferInput(**base)


def test_good_offer_scores_high_no_kills():
    r = score_offer(_good_offer())
    assert not r.killed and r.score > 70
    assert r.provenance["epc"] == "feed"


def test_kill_refund():
    r = score_offer(_good_offer(refund_rate=0.18))
    assert r.killed and "refund>15%" in r.kill_flags and r.score == 0.0


def test_kill_low_gravity():
    assert "gravity<8" in score_offer(_good_offer(gravity=3.0)).kill_flags


def test_kill_saturated_gravity():
    assert "gravity>150_saturated" in score_offer(_good_offer(gravity=400.0)).kill_flags


def test_kill_high_claim_risk():
    assert "claim_risk_HIGH" in score_offer(_good_offer(claim_risk="HIGH")).kill_flags


def test_kill_cookie_and_net90_stack():
    r = score_offer(_good_offer(cookie_days=7, payout_terms="Net-90"))
    assert "cookie<14d" in r.kill_flags and "net90_payout" in r.kill_flags


def test_kill_saas_downgrade_reset():
    r = score_offer(_good_offer(network="partnerstack", gravity=None,
                                commission_resets_on_downgrade=True))
    assert "commission_resets_on_downgrade" in r.kill_flags


def test_saas_no_gravity_requirement():
    r = score_offer(_good_offer(network="partnerstack", gravity=None))
    assert not r.killed


def test_ds24_no_history_kill():
    r = score_offer(_good_offer(network="digistore24", gravity=None, has_sales_history=False))
    assert "no_sales_history" in r.kill_flags


def test_missing_epc_scores_conservatively():
    r = score_offer(_good_offer(epc=None))
    assert not r.killed and r.components["epc"] == 0.0


def test_rank_orders_and_filters():
    offers = [
        _good_offer(name="A", epc=1.5),
        _good_offer(name="B", epc=0.5),
        _good_offer(name="DEAD", refund_rate=0.2),
    ]
    ranked = rank_candidates(offers)
    names = [n for n, _ in ranked]
    assert names == ["A", "B"] and "DEAD" not in names
