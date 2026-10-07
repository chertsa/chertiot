"""Marketing-site content model (app/site_content.py) stays internally consistent: every component
referenced by the lifecycle, the data-flow edges and the journeys exists in the layered diagram."""

from app.site_content import EDGES, site_content


def _identity(s: str) -> str:
    return s


def test_references_resolve_to_diagram_components() -> None:
    site = site_content(_identity)
    ids = [nid for layer in site["layers"] for (nid, *_rest) in layer["nodes"]]
    assert len(ids) == len(set(ids)), "duplicate component id"
    known = set(ids)
    for stage in site["lifecycle"]:
        assert set(stage["components"]) <= known, stage["title"]
    for src, dst in EDGES:
        assert src in known and dst in known, (src, dst)
    for journey in site["journeys"]:
        assert journey["steps"], journey["id"]
        for nid, _text in journey["steps"]:
            assert nid in known, (journey["id"], nid)


def test_every_component_has_detail_and_a_lifecycle_stage() -> None:
    nodes = site_content(_identity)["payload"]["nodes"]
    for nid, node in nodes.items():
        assert node["detail"], nid
        assert node["stages"], f"{nid} is not used by any lifecycle stage"


def test_lifecycle_wheel_positions_are_on_the_ring() -> None:
    stages = site_content(_identity)["lifecycle"]
    assert [s["n"] for s in stages] == list(range(1, len(stages) + 1))
    first = stages[0]
    assert (first["x"], first["y"]) == (50.0, 8.0)  # stage 1 at 12 o'clock
    for s in stages:
        assert 0 <= s["x"] <= 100 and 0 <= s["y"] <= 100
