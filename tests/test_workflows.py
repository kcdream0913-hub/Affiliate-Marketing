"""Sprint 3 gate: workflow JSON integrity + guardrail presence + no inline secrets."""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

WF_DIR = os.path.join(os.path.dirname(__file__), "..", "workflows")
SECRET_PAT = re.compile(r"(sk-[a-zA-Z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9]{16,}|Bearer [A-Za-z0-9._-]{20,})")


def _load_all():
    files = sorted(glob.glob(os.path.join(WF_DIR, "*.json")))
    assert len(files) >= 5, f"expected >=5 workflows, found {len(files)}"
    return {os.path.basename(p): json.load(open(p, encoding="utf-8")) for p in files}


def test_all_workflows_valid_json_with_nodes_and_connections():
    for name, wf in _load_all().items():
        assert wf.get("name"), name
        assert isinstance(wf.get("nodes"), list) and wf["nodes"], name
        assert isinstance(wf.get("connections"), dict), name


def test_connection_referential_integrity():
    for name, wf in _load_all().items():
        node_names = {n["name"] for n in wf["nodes"]}
        for src, outs in wf["connections"].items():
            assert src in node_names, f"{name}: connection source '{src}' missing"
            for branch in outs.get("main", []):
                for tgt in branch:
                    assert tgt["node"] in node_names, f"{name}: target '{tgt['node']}' missing"


def test_every_node_has_type_and_position():
    for name, wf in _load_all().items():
        for n in wf["nodes"]:
            assert n.get("type", "").startswith("n8n-nodes-base."), f"{name}/{n.get('name')}"
            assert "typeVersion" in n and "position" in n, f"{name}/{n.get('name')}"


def test_no_inline_secrets_anywhere():
    for name, wf in _load_all().items():
        blob = json.dumps(wf)
        assert not SECRET_PAT.search(blob), f"{name}: possible inline secret"
        # credentials must be name-references only (n8n binds at instance level)
        for n in wf["nodes"]:
            for cred in (n.get("credentials") or {}).values():
                assert set(cred.keys()) <= {"name", "id"}, f"{name}/{n['name']}: raw credential material"


def test_script_workflow_has_compliance_gate_before_save():
    wf = _load_all()["02-script-copy.json"]
    names = [n["name"] for n in wf["nodes"]]
    assert "Compliance Gate" in names and "Passed Gate?" in names
    # gate must route the FALSE branch to an alert, not to save
    branches = wf["connections"]["Passed Gate?"]["main"]
    true_targets = {t["node"] for t in branches[0]}
    false_targets = {t["node"] for t in branches[1]}
    assert "Save Draft Video Row" in true_targets
    assert "Alert HIGH Block" in false_targets and "Save Draft Video Row" not in false_targets


def test_posting_workflow_has_approval_and_warming():
    wf = _load_all()["05-posting-approval.json"]
    names = [n["name"] for n in wf["nodes"]]
    assert "Telegram Approval" in names, "human approval gate missing (guardrail)"
    assert "Warming Guard" in names, "account-warming guard missing (guardrail)"
    blob = json.dumps(wf)
    assert "sendAndWait" in blob, "approval must block until human responds"
    assert "is_ai_generated" in blob, "AI-disclosure toggle missing on post"


def test_assembly_workflow_burns_label_and_marks_c2pa():
    wf = _load_all()["04-video-assembly.json"]
    blob = json.dumps(wf)
    assert "video_assembly.sh" in blob
    assert "ai_labeled" in blob and "c2pa_present" in blob


def test_caption_always_ad_prefixed_in_script_workflow():
    blob = json.dumps(_load_all()["02-script-copy.json"])
    assert "startsWith('#ad')" in blob or "startsWith(\\\"#ad\\\")" in blob or "#ad " in blob
