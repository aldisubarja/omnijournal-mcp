from omnijournal.models import Paper


def test_doi_normalization():
    p = Paper(title="x", doi="https://doi.org/10.1234/abc", source="s")
    assert p.doi == "10.1234/abc"
