from src.code_search import TrigramRegexSearcher, required_trigrams


class TestTrigramExtraction:

  def test_required_trigrams(self):
    # Basic literal string
    assert required_trigrams("hello") == {"hel", "ell", "llo"}

    # Alternation intersection
    assert required_trigrams("(hello|yellow)") == {"llo", "ell"}

    # No guarantees
    assert required_trigrams("h.*o") == set()

    # Quantified with min > 0
    assert required_trigrams("(abc){1,3}") == {"abc"}

    # Quantified with min = 0
    assert required_trigrams("(abc){0,3}") == set()

    # Complex case
    assert required_trigrams("(foo|bar)baz") == {"baz"}

    # Longer literals
    assert required_trigrams("abcdefg") == {"abc", "bcd", "cde", "def", "efg"}

    # Special regex
    assert required_trigrams(r"\d{3}-\d{3}-\d{4}") == set()


class TestTrigramRegexSearcher:

  def test_basic_search(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "hello world")
    searcher.add_document(2, "goodbye world")
    searcher.add_document(3, "hello there")

    assert set(searcher.search("hello")) == {1, 3}
    assert set(searcher.search("world")) == {1, 2}
    assert set(searcher.search("goodbye")) == {2}
    assert set(searcher.search("there")) == {3}
    assert set(searcher.search("nothing")) == set()

  def test_regex_patterns(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "hello123")
    searcher.add_document(2, "world456")
    searcher.add_document(3, "hello789")

    assert set(searcher.search(r"hello\d+")) == {1, 3}
    assert set(searcher.search(r"\w+\d{3}")) == {1, 2, 3}
    assert set(searcher.search(r"wo.ld\d+")) == {2}

  def test_no_trigrams(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "a")
    searcher.add_document(2, "ab")
    searcher.add_document(3, "abc")
    searcher.add_document(4, "longer text with ab in it")

    assert set(searcher.search(r"ab")) == {2, 3, 4}
    assert set(searcher.search(r"\w{1,2}")) == {1, 2, 3, 4}

  def test_play_examples(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "Efficient regex search using trigram indexing improves speed.")
    searcher.add_document(2, "foo baz bar baz")
    searcher.add_document(3, "hellohello world!")  # two hellos, no spaces
    searcher.add_document(4, "nothing relevant here.")

    assert searcher.search(r"trigram indexing") == [1]
    assert searcher.search(r"(foo|bar)baz") == []  # space breaks match
    assert searcher.search(r"(foo|bar)") == [2]
    assert searcher.search(r"(?:hello){2,} world") == [3]

  def test_overlapping_trigrams(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "aaaaa")
    searcher.add_document(2, "aaabbb")

    assert set(searcher.search(r"aaa")) == {1, 2}
    assert set(searcher.search(r"aaaa")) == {1}
    assert set(searcher.search(r"aaaaa")) == {1}

  def test_multiple_documents_same_trigram(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "abc")
    searcher.add_document(2, "abc")
    searcher.add_document(3, "xyz")

    assert set(searcher.search(r"abc")) == {1, 2}
    assert set(searcher.search(r"xyz")) == {3}
    assert set(searcher.search(r"a.*c")) == {1, 2}


class TestEdgeCases:

  def test_empty_searcher(self):
    searcher = TrigramRegexSearcher()
    assert searcher.search("anything") == []

  def test_empty_query(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "some content")
    assert set(searcher.search("")) == {1}  # Empty regex matches everything

  def test_unicode_support(self):
    searcher = TrigramRegexSearcher()
    searcher.add_document(1, "café au lait")
    searcher.add_document(2, "cafeteria")

    assert set(searcher.search("café")) == {1}
