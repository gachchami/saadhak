import json

from saadhak.witness import journal


def test_chain_verifies_and_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL_DIR", tmp_path)
    journal.append("cycle_start", {"cycle_id": "c1"})
    journal.append("gate_result", {"decision": "refuse"})
    ok, msg = journal.verify()
    assert ok, msg

    p = journal.path_for()
    lines = p.read_text().splitlines()
    rec = json.loads(lines[0]); rec["data"]["cycle_id"] = "tampered"
    lines[0] = json.dumps(rec)
    p.write_text("\n".join(lines) + "\n")

    ok, msg = journal.verify()
    assert not ok and "hash mismatch" in msg
