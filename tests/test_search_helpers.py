from omnijournal.search import detect_search_type, deduplicate_and_merge
from omnijournal.providers import SearchType
from omnijournal.models import Paper


def test_detect_search_type():
    assert detect_search_type("10.1038/nature12373") == SearchType.DOI
    assert detect_search_type("Smith, J") == SearchType.AUTHOR
    assert detect_search_type("transformer attention") == SearchType.KEYWORDS


def test_deduplicate_and_merge_prefers_higher_priority():
    a = Paper(title="Test Paper", doi="10.1/abc", source="a", source_priority=100, venue="Venue A")
    b = Paper(title="Test Paper", doi="10.1/abc", source="b", source_priority=200, venue="Venue B", citation_count=50)
    merged = deduplicate_and_merge([a, b])
    assert len(merged) == 1
    assert merged[0].venue == "Venue B"
    assert merged[0].citation_count == 50
    assert set(merged[0].sources_seen) >= {"a", "b"}
