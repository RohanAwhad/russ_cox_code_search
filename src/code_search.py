import re, sre_parse
from collections import defaultdict

# ----------------------------  Trigram extraction  ----------------------------
def _subpattern_from_data(state, branch_data):
    sp = sre_parse.SubPattern(state)
    sp.data = list(branch_data)
    return sp

def _mandatory_trigrams(subpat, required=True) -> set[str]:
    """Return all 3‑character literals that every match must contain."""
    if not required:          # optional part => guarantees vanish
        return set()

    must = set()
    i, data = 0, list(subpat.data)
    while i < len(data):
        op, val = data[i]

        # contiguous run of LITERAL tokens
        if op is sre_parse.LITERAL:
            run = [chr(val)]
            j = i + 1
            while j < len(data) and data[j][0] is sre_parse.LITERAL:
                run.append(chr(data[j][1])); j += 1
            literal = "".join(run)
            for k in range(len(literal) - 2):
                must.add(literal[k : k + 3])
            i = j; continue

        # a parenthesised group
        if op is sre_parse.SUBPATTERN:
            must |= _mandatory_trigrams(val[3], required=True)

        # alternation  (X|Y)  ->  intersection of every branch's guarantees
        elif op is sre_parse.BRANCH:
            branches = val[1]
            branch_sets = [
                _mandatory_trigrams(_subpattern_from_data(subpat.state, b))
                for b in branches
            ]
            if branch_sets:
                common = set(branch_sets[0])
                for s in branch_sets[1:]:
                    common &= s
                must |= common

        # quantified term  X{m,n}  – guaranteed only if m>=1
        elif op is sre_parse.MAX_REPEAT:
            min_rep, _, repeated_subpat = val
            must |= _mandatory_trigrams(repeated_subpat, required=(min_rep > 0))

        # other operators (ANY, IN, CATEGORY, ...) give no guarantees
        i += 1
    return must

def required_trigrams(regex: str) -> set[str]:
    """Exact Russ‑Cox required‑trigram set for `regex`."""
    return _mandatory_trigrams(sre_parse.parse(regex), required=True)

# -------------------------------  Index & search  -----------------------------
class TrigramRegexSearcher:
    def __init__(self):
        self.docs: dict[int, str] = {}
        self.inv:  dict[str, set[int]] = defaultdict(set)

    # indexing
    def add_document(self, doc_id: int, text: str) -> None:
        self.docs[doc_id] = text
        seen = set()
        for i in range(len(text) - 2):
            tg = text[i:i+3]
            if tg not in seen:
                self.inv[tg].add(doc_id); seen.add(tg)

    # querying
    def search(self, pattern: str) -> list[int]:
        req = required_trigrams(pattern)

        # Pre-filter by intersecting posting lists
        if not req:                         # no guarantees -> scan everything
            candidates = set(self.docs)
        else:
            candidates = None
            for tg in req:
                ids = self.inv.get(tg, set())
                candidates = ids.copy() if candidates is None else candidates & ids
            if not candidates:
                return []

        # Exact regex match on the survivors
        rx = re.compile(pattern)
        return [doc for doc in candidates if rx.search(self.docs[doc])]  # there is doc 3 in the candidates
