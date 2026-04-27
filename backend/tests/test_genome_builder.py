"""
Tests for build_genome and build_user_taste_genome (pure functions, no DB).

build_genome constructs a structured text string from a Book's relationships
(tropes, archetypes, genres, tones, pacing). It is the input to the genome
embedding model and must encode all literary metadata deterministically.
"""
from unittest.mock import MagicMock


def _make_book(
    title="Test Book",
    author_name="Test Author",
    tropes=None,      # list of (name, weight)
    archetypes=None,  # list of (name, importance)
    genres=None,      # list of name strings
    tones=None,       # list of name strings
    pacing=None,
):
    book = MagicMock()
    book.title = title
    book.author = MagicMock()
    book.author.name = author_name
    book.pacing = pacing

    bt_list = []
    for name, weight in (tropes or []):
        bt = MagicMock()
        bt.weight = weight
        bt.trope = MagicMock()
        bt.trope.name = name
        bt_list.append(bt)
    book.book_tropes = bt_list

    dna_list = []
    for name, importance in (archetypes or []):
        dna = MagicMock()
        dna.importance = importance
        dna.archetype = MagicMock()
        dna.archetype.name = name
        dna_list.append(dna)
    book.character_dna = dna_list

    genre_list = []
    for name in (genres or []):
        g = MagicMock()
        g.name = name
        genre_list.append(g)
    book.genres = genre_list

    tone_list = []
    for name in (tones or []):
        t = MagicMock()
        t.name = name
        tone_list.append(t)
    book.tones = tone_list

    return book


class TestBuildGenomeHeader:
    def test_includes_title_and_author(self):
        from app.services.embedding import build_genome
        book = _make_book("Dune", "Frank Herbert")
        assert '"Dune" by Frank Herbert.' in build_genome(book)

    def test_no_tropes_omits_tropes_section(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[])
        assert "Tropes:" not in build_genome(book)

    def test_no_archetypes_omits_archetypes_section(self):
        from app.services.embedding import build_genome
        book = _make_book(archetypes=[])
        assert "Character archetypes:" not in build_genome(book)

    def test_no_genres_omits_genres_section(self):
        from app.services.embedding import build_genome
        book = _make_book(genres=[])
        assert "Genres:" not in build_genome(book)

    def test_no_tones_omits_tones_section(self):
        from app.services.embedding import build_genome
        book = _make_book(tones=[])
        assert "Tone:" not in build_genome(book)

    def test_no_pacing_omits_pacing_section(self):
        from app.services.embedding import build_genome
        book = _make_book(pacing=None)
        assert "Pacing:" not in build_genome(book)

    def test_description_never_appears(self):
        """Description is intentionally excluded from the genome string."""
        from app.services.embedding import build_genome
        book = _make_book(title="Dune", author_name="Frank Herbert")
        book.description = "A sweeping tale of desert planets and spice."
        result = build_genome(book)
        assert "sweeping tale" not in result
        assert "spice" not in result


class TestBuildGenomeTropeStrengthLabels:
    def test_dominant_label_at_exactly_0_8(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Chosen One", 0.8)])
        assert "dominant" in build_genome(book)

    def test_dominant_label_above_0_8(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Chosen One", 0.95)])
        assert "dominant" in build_genome(book)

    def test_strong_label_at_exactly_0_6(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Slow Burn", 0.6)])
        assert "strong" in build_genome(book)

    def test_strong_label_between_0_6_and_0_8(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Slow Burn", 0.75)])
        assert "strong" in build_genome(book)

    def test_moderate_label_at_exactly_0_4(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Found Family", 0.4)])
        assert "moderate" in build_genome(book)

    def test_moderate_label_between_0_4_and_0_6(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Found Family", 0.5)])
        assert "moderate" in build_genome(book)

    def test_subtle_label_below_0_4(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Betrayal", 0.3)])
        assert "subtle" in build_genome(book)

    def test_subtle_label_at_zero(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Betrayal", 0.0)])
        assert "subtle" in build_genome(book)

    def test_tropes_sorted_descending_by_weight(self):
        """Highest-weight trope must appear first in the output string."""
        from app.services.embedding import build_genome
        book = _make_book(tropes=[
            ("Slow Burn", 0.5),
            ("Chosen One", 0.9),
            ("Betrayal", 0.2),
        ])
        result = build_genome(book)
        assert result.index("Chosen One") < result.index("Slow Burn") < result.index("Betrayal")

    def test_trope_weight_formatted_to_two_decimals(self):
        from app.services.embedding import build_genome
        book = _make_book(tropes=[("Enemies to Lovers", 0.8)])
        assert "0.80" in build_genome(book)


class TestBuildGenomeSections:
    def test_genres_sorted_alphabetically(self):
        from app.services.embedding import build_genome
        book = _make_book(genres=["Romance", "Fantasy"])
        result = build_genome(book)
        assert result.index("Fantasy") < result.index("Romance")

    def test_tones_present_in_output(self):
        from app.services.embedding import build_genome
        book = _make_book(tones=["Dark", "Witty"])
        result = build_genome(book)
        assert "Dark" in result and "Witty" in result

    def test_pacing_1_very_slow(self):
        from app.services.embedding import build_genome
        assert "very slow" in build_genome(_make_book(pacing=1))

    def test_pacing_2_slow(self):
        from app.services.embedding import build_genome
        assert "slow" in build_genome(_make_book(pacing=2))

    def test_pacing_3_moderate(self):
        from app.services.embedding import build_genome
        assert "moderate" in build_genome(_make_book(pacing=3))

    def test_pacing_4_fast(self):
        from app.services.embedding import build_genome
        assert "fast" in build_genome(_make_book(pacing=4))

    def test_pacing_5_very_fast(self):
        from app.services.embedding import build_genome
        assert "very fast" in build_genome(_make_book(pacing=5))

    def test_archetype_importance_fraction(self):
        from app.services.embedding import build_genome
        book = _make_book(archetypes=[("Reluctant Hero", 8)])
        assert "8/10" in build_genome(book)

    def test_archetypes_sorted_descending_by_importance(self):
        from app.services.embedding import build_genome
        book = _make_book(archetypes=[("Mentor", 3), ("Hero", 9)])
        result = build_genome(book)
        assert result.index("Hero") < result.index("Mentor")

    def test_full_genome_all_fields(self):
        from app.services.embedding import build_genome
        book = _make_book(
            title="Mistborn",
            author_name="Brandon Sanderson",
            tropes=[("Chosen One", 0.9), ("Magic System", 0.7)],
            archetypes=[("Reluctant Hero", 8)],
            genres=["Fantasy"],
            tones=["Dark"],
            pacing=4,
        )
        result = build_genome(book)
        assert '"Mistborn" by Brandon Sanderson.' in result
        assert "Chosen One" in result and "dominant" in result
        assert "Magic System" in result and "strong" in result
        assert "Reluctant Hero" in result and "8/10" in result
        assert "Fantasy" in result
        assert "Dark" in result
        assert "fast" in result


class TestBuildUserTasteGenome:
    def test_empty_returns_base_string_only(self):
        from app.services.embedding import build_user_taste_genome
        result = build_user_taste_genome([], [])
        assert "Reading preferences." in result
        assert "Preferred tropes:" not in result
        assert "Preferred character archetypes:" not in result

    def test_tropes_appear_with_strength_labels(self):
        from app.services.embedding import build_user_taste_genome
        result = build_user_taste_genome([("Enemies to Lovers", 0.85)], [])
        assert "Enemies to Lovers" in result
        assert "dominant" in result

    def test_archetypes_appear_with_importance(self):
        from app.services.embedding import build_user_taste_genome
        result = build_user_taste_genome([], [("Reluctant Hero", 7)])
        assert "Reluctant Hero" in result
        assert "7/10" in result

    def test_both_tropes_and_archetypes(self):
        from app.services.embedding import build_user_taste_genome
        result = build_user_taste_genome(
            [("Slow Burn", 0.6)], [("Anti-Hero", 5)]
        )
        assert "Slow Burn" in result
        assert "Anti-Hero" in result
