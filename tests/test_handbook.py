from app.handbook import read_handbook, slugify, to_records
from scripts.upload_handbook import stale_ids


def test_every_section_becomes_a_record():
    records = to_records(read_handbook())
    assert len(records) == 25
    assert all(r["chunk_text"].startswith(f"# {r['section']}") for r in records)


def test_record_ids_are_unique():
    ids = [r["id"] for r in to_records(read_handbook())]
    assert len(ids) == len(set(ids))


def test_slugify():
    assert slugify("Parental Leave and Benefits") == "parental-leave-and-benefits"


def test_handbook_stays_in_universe():
    text = read_handbook().lower()
    for word in ["made up", "demo", "fictional"]:
        assert word not in text


def test_renamed_sections_count_as_stale():
    records = [{"id": "compensation"}, {"id": "dress-code"}]
    assert stale_ids(["pay", "compensation", "dress-code"], records) == ["pay"]
