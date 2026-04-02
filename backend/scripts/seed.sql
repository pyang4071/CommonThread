-- Seed data for CommonThread
-- Run in Supabase SQL Editor if the API seed script can't reach the backend

-- Tropes
INSERT INTO tropes (name, category, description) VALUES
  ('Enemies to Lovers', 'Romance',   'Two rivals slowly fall in love.'),
  ('Chosen One',        'Fantasy',   'A protagonist destined to save the world.'),
  ('Found Family',      'Character', 'A group of unlikely companions becomes family.'),
  ('Slow Burn',         'Romance',   'Romantic tension builds gradually over time.'),
  ('Unreliable Narrator','Narrative','The storyteller''s account cannot be fully trusted.'),
  ('Redemption Arc',    'Character', 'A villain or flawed character earns forgiveness.'),
  ('Dark Academia',     'Setting',   'Elite schools, secret societies, and obsessive scholarship.'),
  ('Dual Timeline',     'Narrative', 'Story alternates between two time periods.'),
  ('Forbidden Love',    'Romance',   'Romance opposed by society, family, or circumstance.'),
  ('Magic System',      'Fantasy',   'A structured, rule-based system of magic.')
ON CONFLICT (name) DO NOTHING;

-- Archetypes
INSERT INTO archetypes (name, description) VALUES
  ('The Hero',    'Brave, driven by a noble goal.'),
  ('The Mentor',  'Wise guide who helps the protagonist grow.'),
  ('The Trickster','Cunning, unpredictable, challenges norms.'),
  ('The Shadow',  'The villain or dark mirror of the hero.'),
  ('The Lover',   'Driven by passion and deep emotional connection.')
ON CONFLICT (name) DO NOTHING;

-- Books
INSERT INTO books (title, author, isbn, publication_date) VALUES
  ('The Name of the Wind',          'Patrick Rothfuss', '9780756404741', '2007-03-27'),
  ('The Wise Man''s Fear',           'Patrick Rothfuss', '9780756404734', '2011-03-01'),
  ('The Secret History',            'Donna Tartt',      '9780679410324', '1992-09-16'),
  ('If We Were Villains',           'M.L. Rio',         '9781250095299', '2017-04-11'),
  ('The Cruel Prince',              'Holly Black',      '9780316310277', '2018-01-02'),
  ('A Court of Thorns and Roses',   'Sarah J. Maas',    '9781619634442', '2015-05-05'),
  ('Fourth Wing',                   'Rebecca Yarros',   '9781649374042', '2023-05-02'),
  ('The Atlas Six',                 'Olivie Blake',     '9781250854513', '2022-03-01'),
  ('Piranesi',                      'Susanna Clarke',   '9781635575637', '2020-09-15'),
  ('Jonathan Strange & Mr Norrell', 'Susanna Clarke',   '9781582344164', '2004-09-08')
ON CONFLICT (isbn) DO NOTHING;

-- Book-Trope weights
INSERT INTO book_tropes (book_id, trope_id, weight)
SELECT b.book_id, t.trope_id, v.weight
FROM (VALUES
  ('The Name of the Wind',          'Chosen One',          0.9),
  ('The Name of the Wind',          'Magic System',        0.8),
  ('The Name of the Wind',          'Unreliable Narrator', 0.7),
  ('The Wise Man''s Fear',           'Chosen One',          0.8),
  ('The Wise Man''s Fear',           'Slow Burn',           0.6),
  ('The Wise Man''s Fear',           'Magic System',        0.7),
  ('The Secret History',            'Dark Academia',       0.95),
  ('The Secret History',            'Unreliable Narrator', 0.85),
  ('The Secret History',            'Found Family',        0.5),
  ('If We Were Villains',           'Dark Academia',       0.9),
  ('If We Were Villains',           'Found Family',        0.7),
  ('If We Were Villains',           'Unreliable Narrator', 0.75),
  ('The Cruel Prince',              'Enemies to Lovers',   0.9),
  ('The Cruel Prince',              'Forbidden Love',      0.8),
  ('The Cruel Prince',              'Chosen One',          0.5),
  ('A Court of Thorns and Roses',   'Enemies to Lovers',   0.85),
  ('A Court of Thorns and Roses',   'Forbidden Love',      0.9),
  ('A Court of Thorns and Roses',   'Slow Burn',           0.7),
  ('Fourth Wing',                   'Enemies to Lovers',   0.9),
  ('Fourth Wing',                   'Slow Burn',           0.8),
  ('Fourth Wing',                   'Magic System',        0.6),
  ('The Atlas Six',                 'Dark Academia',       0.85),
  ('The Atlas Six',                 'Magic System',        0.8),
  ('The Atlas Six',                 'Chosen One',          0.5),
  ('Piranesi',                      'Unreliable Narrator', 0.95),
  ('Piranesi',                      'Dual Timeline',       0.6),
  ('Jonathan Strange & Mr Norrell', 'Magic System',        0.9),
  ('Jonathan Strange & Mr Norrell', 'Dual Timeline',       0.5),
  ('Jonathan Strange & Mr Norrell', 'Redemption Arc',      0.6)
) AS v(book_title, trope_name, weight)
JOIN books b ON b.title = v.book_title
JOIN tropes t ON t.name = v.trope_name
ON CONFLICT DO NOTHING;

-- Character DNA
INSERT INTO character_dna (book_id, archetype_id, importance)
SELECT b.book_id, a.archetype_id, v.importance
FROM (VALUES
  ('The Name of the Wind',          'The Hero',     9),
  ('The Name of the Wind',          'The Trickster',7),
  ('The Wise Man''s Fear',           'The Hero',     8),
  ('The Wise Man''s Fear',           'The Lover',    6),
  ('The Secret History',            'The Shadow',   8),
  ('The Secret History',            'The Trickster',6),
  ('If We Were Villains',           'The Shadow',   7),
  ('If We Were Villains',           'The Hero',     5),
  ('The Cruel Prince',              'The Shadow',   9),
  ('The Cruel Prince',              'The Trickster',8),
  ('A Court of Thorns and Roses',   'The Lover',    9),
  ('A Court of Thorns and Roses',   'The Hero',     7),
  ('Fourth Wing',                   'The Hero',     8),
  ('Fourth Wing',                   'The Lover',    8),
  ('The Atlas Six',                 'The Trickster',9),
  ('The Atlas Six',                 'The Shadow',   7),
  ('Piranesi',                      'The Hero',     6),
  ('Piranesi',                      'The Mentor',   5),
  ('Jonathan Strange & Mr Norrell', 'The Mentor',   8),
  ('Jonathan Strange & Mr Norrell', 'The Hero',     7)
) AS v(book_title, archetype_name, importance)
JOIN books b ON b.title = v.book_title
JOIN archetypes a ON a.name = v.archetype_name
ON CONFLICT DO NOTHING;
