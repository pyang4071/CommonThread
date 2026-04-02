"""
Clustering helpers for similarity candidate reduction.

Planned clusters:
  - Books grouped by author (Books.author index)
  - Tropes grouped by category (Tropes.category index)

These clusters act as pre-filters: compute full similarity only within
or across adjacent clusters rather than all-pairs across the entire library.
"""
