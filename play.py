from src import code_search

# -------------------------------  Quick demo  --------------------------------
if __name__ == "__main__":
    s = code_search.TrigramRegexSearcher()
    s.add_document(1, "Efficient regex search using trigram indexing improves speed.")
    s.add_document(2, "foo baz bar baz")
    s.add_document(3, "hellohello world!")           # two hellos, no spaces
    s.add_document(4, "nothing relevant here.")

    print(s.search(r"trigram indexing"))        # -> [1]
    print(s.search(r"(foo|bar)baz"))            # -> []  (space breaks match)
    print(s.search(r"(foo|bar)"))               # -> [2]
    print(s.search(r"(?:hello){2,} world"))      # -> [3]
