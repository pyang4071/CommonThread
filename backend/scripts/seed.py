"""
Seed the database with 15 well-known books and all related data.

Usage:
    uv run python scripts/seed.py
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.engine import AsyncSessionLocal
from app.models.archetype import Archetype
from app.models.author import Author
from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_trope import BookTrope
from app.models.book_type import BookType
from app.models.character_dna import CharacterDNA
from app.models.genre import Genre
from app.models.tone import Tone
from app.models.trope import Trope
from app.services.embedding import embed_book


# ── Reference data ─────────────────────────────────────────────────────────────

GENRES = [
    {"name": "Fantasy",            "description": "Worlds with magic, mythical creatures, and the impossible made real."},
    {"name": "Science Fiction",    "description": "Speculative futures, technology, and encounters with the unknown."},
    {"name": "Mystery",            "description": "Puzzles, crimes, and the search for hidden truths."},
    {"name": "Thriller",           "description": "Suspense-driven plots with high stakes, constant tension, and fast pacing."},
    {"name": "Horror",             "description": "Stories designed to frighten, unsettle, or disturb."},
    {"name": "Romance",            "description": "Stories centred on love, desire, and emotional relationships."},
    {"name": "Historical Fiction", "description": "Stories set against real historical backdrops with invented characters or events."},
    {"name": "Literary Fiction",   "description": "Character-driven, prose-focused work that prioritises artistic ambition over plot."},
    {"name": "Contemporary Fiction","description": "Realistic fiction set in the present day."},
    {"name": "Classic",            "description": "Enduring works recognised as foundational or landmark achievements in literature."},
    {"name": "Dystopian",          "description": "Speculative fiction set in oppressive, dehumanising societies."},
    {"name": "Paranormal",         "description": "Fiction featuring ghosts, vampires, werewolves, or other supernatural phenomena."},
    {"name": "Magical Realism",    "description": "Realistic settings where magical elements appear naturally, without explanation."},
    {"name": "Crime",              "description": "Fiction centred on criminal acts, investigations, and their consequences."},
    {"name": "Adventure",          "description": "Plot-driven stories featuring journeys, physical danger, and high-stakes action."},
    {"name": "Gothic",             "description": "Dark, atmospheric fiction defined by decay, secrets, and psychological dread."},
    {"name": "Humor / Satire",     "description": "Fiction that uses comedy or irony to entertain or critique."},
    {"name": "Mythology / Folklore","description": "Stories drawing heavily on myth, legend, or oral tradition."},
    {"name": "Young Adult",        "description": "Fiction written for teenage audiences, typically with a young protagonist."},
    {"name": "Middle Grade",       "description": "Fiction written for readers aged 8–12; coming-of-age and adventure focus."},
]

BOOK_TYPES = [
    {"name": "Standalone",           "description": "A complete, self-contained story in a single volume."},
    {"name": "Series Starter",       "description": "The first book in an ongoing multi-volume series."},
    {"name": "Novel",                "description": "Full-length prose fiction (typically 70 000+ words)."},
    {"name": "Novella",              "description": "Mid-length prose fiction (typically 20 000–70 000 words)."},
    {"name": "Short Story Collection","description": "A volume collecting multiple short stories by a single author."},
    {"name": "Anthology",            "description": "A volume collecting work by multiple authors, usually around a theme."},
    {"name": "Graphic Novel",        "description": "Long-form sequential art / illustrated narrative."},
    {"name": "YA",                   "description": "Young Adult — written for teenage audiences."},
    {"name": "Middle Grade",         "description": "Written for readers aged 8–12."},
    {"name": "Adult",                "description": "Content and themes aimed at adult readers."},
    {"name": "New Adult",            "description": "Themes centred on early adulthood (college, first jobs, early relationships)."},
]

# category → list of (name, description)
TROPES = {
    "Romance": [
        ("Enemies to Lovers",    "Two characters begin as rivals or enemies before falling in love."),
        ("Forbidden Love",       "A romance that society, circumstance, or law forbids."),
        ("Slow Burn Romance",    "Romantic tension that builds gradually over a long stretch of the story."),
        ("Love Triangle",        "A protagonist torn between two potential romantic partners."),
        ("Fake Dating",          "Characters pretend to be a couple and develop real feelings in the process."),
        ("Friends to Lovers",    "A close friendship slowly transforms into a romantic relationship."),
        ("Forced Proximity",     "Circumstances trap two characters together, accelerating emotional intimacy."),
        ("Second Chance Romance","Former lovers are reunited after separation and must rediscover each other."),
        ("Grumpy x Sunshine",    "An uptight or cynical character is paired with an irrepressibly warm one."),
        ("Marriage of Convenience","Characters enter a marriage for practical reasons and fall in love along the way."),
        ("Star-Crossed Lovers",  "Two people deeply in love are kept apart by forces beyond their control."),
    ],
    "Character": [
        ("Chosen One",        "A character prophesied or uniquely destined to change the world."),
        ("Coming of Age",     "A protagonist's journey from innocence or youth to maturity and self-knowledge."),
        ("Redemption Arc",    "A morally compromised character earns their way back through sacrifice or growth."),
        ("Anti-Hero",         "A protagonist who lacks conventional heroic virtues but drives the story forward."),
        ("Reluctant Hero",    "A character who avoids the call to action but is ultimately forced to rise."),
        ("Fish Out of Water", "A character thrust into an unfamiliar world or social context where they don't fit."),
        ("Corrupted Mentor",  "A guide or authority figure whose wisdom turns into control or betrayal."),
        ("Villain Protagonist","The story is driven by a character who is explicitly the antagonist or morally irredeemable."),
    ],
    "Narrative": [
        ("Unreliable Narrator","The story is filtered through a narrator whose account cannot be fully trusted."),
        ("Secret Identity",   "A major character conceals who they truly are."),
        ("Revenge",           "A character's primary motivation is retribution for a past wrong."),
        ("Tragedy",           "The protagonist's downfall is driven by their own flaws or the cruelty of fate."),
        ("In Medias Res",     "The story begins in the middle of the action, with context revealed gradually."),
        ("Dual Timeline",     "The narrative alternates between two time periods whose connection slowly becomes clear."),
        ("Twist Ending",      "A revelation near the end fundamentally reframes everything the reader thought they knew."),
        ("Frame Narrative",   "An outer story contains or introduces an inner story being told by a character."),
    ],
    "Worldbuilding": [
        ("Magic System",          "A defined, rule-bound structure for how magic works in the world."),
        ("Hidden World",          "A fantastical realm or society concealed from ordinary awareness."),
        ("Dark Academia",         "An elite academic setting infused with obsession, ambition, and moral danger."),
        ("Post-Apocalyptic Setting","The story takes place in the ruins of a collapsed civilization."),
        ("Dystopian Society",     "A totalitarian or deeply unjust society that characters must navigate or resist."),
        ("Secondary World",       "The story takes place in a fully invented world unconnected to our own."),
        ("Soft Magic",            "Magic exists but its rules are vague or deliberately mysterious."),
    ],
    "Plot": [
        ("Found Family",           "Characters who are not related by blood form a family-like bond through shared experience."),
        ("The Heist",              "A team assembles to pull off a complex, high-stakes theft or con."),
        ("Political Intrigue",     "Power struggles, factions, and scheming at a societal or governmental level."),
        ("Tournament/Competition", "Characters compete in a structured contest with high personal or societal stakes."),
        ("Quest",                  "A protagonist journeys toward a specific goal, gathering allies and facing trials."),
        ("Prophecy",               "A foretold event shapes the characters' choices and the story's trajectory."),
        ("Betrayal",               "A trusted character proves false, shattering alliances and forcing reckonings."),
        ("Forbidden Knowledge",    "Pursuing or possessing certain knowledge carries catastrophic consequences."),
        ("Last Stand",             "A group or individual makes a desperate, often sacrificial final effort against overwhelming odds."),
        ("Mistaken Identity",      "Confusion about who someone is drives the plot's conflict or comedy."),
        ("Reverse Whodunit",       "The audience knows who committed the crime; tension comes from how (or if) they are caught."),
    ],
    "Mystery & Thriller": [
        ("Locked Room Mystery","A crime appears to have been committed in a space with no possible entry or exit."),
        ("Cold Case",         "An unsolved past crime resurfaces and must be reopened."),
        ("Corrupt Authority", "The institutions meant to protect people are themselves the source of danger."),
        ("The Mole",          "A trusted member of a group is secretly working against them."),
        ("Against the Clock", "The protagonist must solve the problem or avert disaster before a hard deadline."),
        ("Conspiracy",        "A hidden network of powerful actors is manipulating events from behind the scenes."),
    ],
    "Horror & Gothic": [
        ("Haunted Setting",      "A location — house, town, ship — is itself a source of malevolent or uncanny presence."),
        ("Body Horror",          "The human body is transformed, invaded, or violated in disturbing ways."),
        ("Psychological Unreality","The line between what is real and what is in the protagonist's mind becomes dangerously blurred."),
        ("Cosmic Horror",        "Forces of incomprehensible scale and indifference reduce human existence to insignificance."),
        ("Gothic Atmosphere",    "Decaying grandeur, repressed secrets, and ancestral curses define the setting and mood."),
    ],
    "Science Fiction": [
        ("First Contact",       "Humanity encounters an alien intelligence for the first time."),
        ("AI Consciousness",    "An artificial intelligence develops self-awareness with unpredictable consequences."),
        ("Time Travel",         "Characters move between time periods, often creating paradoxes or moral dilemmas."),
        ("Generation Ship",     "A massive vessel carries humanity across space over centuries; conflicts arise from isolation and time."),
        ("Human Enhancement",   "Characters are modified — genetically, cybernetically, or chemically — raising questions of identity and ethics."),
        ("Climate Collapse",    "Environmental catastrophe reshapes society and drives the story's conflict."),
    ],
}

ARCHETYPES = [
    ("The Hero",        "A figure who rises to meet an extraordinary challenge and embodies the story's moral center."),
    ("The Mentor",      "A wise guide who shapes the protagonist's growth, often at personal cost."),
    ("The Trickster",   "Cunning and unpredictable — uses wit, deception, and chaos to achieve their ends."),
    ("The Shadow",      "The dark reflection of the hero; embodies suppressed fears, desires, or the cost of power."),
    ("The Rebel",       "Defies authority and convention, driven by a belief that the existing order is wrong."),
    ("The Lover",       "Driven by passion, beauty, and the need for deep connection with another person or ideal."),
    ("The Sage",        "Pursues knowledge and truth above all else; wisdom is both gift and burden."),
    ("The Caregiver",   "Nurtures and sacrifices for others, often at serious personal cost."),
    ("The Explorer",    "Driven by restless curiosity and the need to discover what lies beyond the known."),
    ("The Ruler",       "Seeks order, control, and power — often paying a moral price to hold it."),
    ("The Outcast",     "Lives on society's margins, misunderstood and searching for belonging or purpose."),
    ("The Tragic Hero", "Noble and gifted, but undone by a fatal flaw or the cruelty of circumstance."),
    ("The Innocent",    "Enters the world with pure intentions and uncorrupted hope; their loss of innocence is often central."),
    ("The Survivor",    "Has endured catastrophic loss or trauma and is defined by what they carry forward."),
    ("The Villain",     "Actively opposes the protagonist with intelligence, conviction, or genuine menace."),
    ("The Protector",   "Puts others' safety above their own, defined by guardianship and sacrifice."),
    ("The Anti-Hero",   "Driven by self-interest, cynicism, or questionable means — but produces outcomes that matter."),
    ("The Everyman",    "An ordinary person caught up in extraordinary events; the reader's anchor in the story."),
]

TONES = [
    "Dark",
    "Cozy",
    "Hopeful",
    "Melancholy",
    "Tense",
    "Atmospheric",
    "Whimsical",
    "Gritty",
    "Romantic",
    "Humorous",
    "Satirical",
    "Philosophical",
    "Heartwarming",
    "Bittersweet",
    "Lyrical",
    "Nostalgic",
    "Disturbing",
    "Action-Packed",
    "Slow Burn",
    "Witty",
]

BOOKS = [
    {
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "isbn": "978-0-7564-0407-9",
        "pub_date": "2007-03-27",
        "description": (
            "Told in Kvothe's own words, this is the tale of the magically gifted young man "
            "who grows to be the most notorious wizard his world has ever seen. From his "
            "childhood in a troupe of traveling players, to years spent as a near-feral orphan "
            "in a crime-ridden city, to his brazen bid to enter a legendary school of magic, "
            "The Name of the Wind is a masterwork of epic fantasy."
        ),
        "genres": ["Fantasy"],
        "book_types": ["Novel", "Adult", "Series Starter"],
        "tropes": [
            ("Magic System", 0.85),
            ("Chosen One", 0.65),
            ("Coming of Age", 0.65),
            ("Unreliable Narrator", 0.45),
        ],
        "archetypes": [("The Hero", 9), ("The Trickster", 8), ("The Sage", 6)],
    },
    {
        "title": "The Wise Man's Fear",
        "author": "Patrick Rothfuss",
        "isbn": "978-0-7564-0473-4",
        "pub_date": "2011-03-01",
        "description": (
            "Kvothe takes a semester of absence from the University and travels to Vintas, "
            "where he earns a place with the Maer Alveron. Sent into the wilderness to deal "
            "with bandits, he studies with the Adem mercenaries and comes closer to the truth "
            "of the Chandrian — the beings who murdered his family."
        ),
        "genres": ["Fantasy"],
        "book_types": ["Novel", "Adult"],
        "tropes": [
            ("Magic System", 0.85),
            ("Political Intrigue", 0.65),
            ("Coming of Age", 0.45),
            ("Chosen One", 0.45),
        ],
        "archetypes": [("The Hero", 9), ("The Trickster", 8), ("The Sage", 5)],
    },
    {
        "title": "Fourth Wing",
        "author": "Rebecca Yarros",
        "isbn": "978-1-64937-519-4",
        "pub_date": "2023-05-02",
        "description": (
            "Twenty-year-old Violet Sorrengail was supposed to enter the Scribe Quadrant, "
            "but her commanding-general mother forces her into the most lethal division: "
            "the Riders Quadrant, where students bond with war dragons or die trying. "
            "Surviving the brutal first year means crossing paths — and clashing — with "
            "the most powerful and dangerous rider in her year."
        ),
        "genres": ["Fantasy", "Romance"],
        "book_types": ["Novel", "Adult", "Series Starter"],
        "tropes": [
            ("Enemies to Lovers", 0.85),
            ("Magic System", 0.65),
            ("Forbidden Love", 0.65),
            ("Tournament/Competition", 0.45),
            ("Chosen One", 0.25),
        ],
        "archetypes": [("The Lover", 9), ("The Hero", 8), ("The Rebel", 7)],
    },
    {
        "title": "A Court of Thorns and Roses",
        "author": "Sarah J. Maas",
        "isbn": "978-1-61963-384-9",
        "pub_date": "2015-05-05",
        "description": (
            "Nineteen-year-old huntress Feyre kills a wolf in the woods and is dragged to "
            "a treacherous magical land by the faerie Tamlin. As she adapts to her captivity, "
            "her hostility turns to something far more dangerous. But an ancient, wicked curse "
            "is spreading, and breaking it may cost more than her life."
        ),
        "genres": ["Fantasy", "Romance"],
        "book_types": ["Novel", "Adult", "Series Starter"],
        "tropes": [
            ("Forbidden Love", 0.85),
            ("Enemies to Lovers", 0.65),
            ("Hidden World", 0.65),
            ("Slow Burn Romance", 0.45),
        ],
        "archetypes": [("The Lover", 9), ("The Hero", 8), ("The Shadow", 6)],
    },
    {
        "title": "The Atlas Six",
        "author": "Olivie Blake",
        "isbn": "978-1-250-85443-4",
        "pub_date": "2020-01-01",
        "description": (
            "Six gifted young magicians are recruited by the Alexandrian Society — a secret "
            "organisation that has hoarded the world's most dangerous knowledge for millennia. "
            "They are given one year in the archives. At the end, only five will be initiated. "
            "The sixth will be eliminated. A dark, cerebral fantasy about power, morality, "
            "and what we sacrifice for knowledge."
        ),
        "genres": ["Fantasy"],
        "book_types": ["Novel", "Adult", "Series Starter"],
        "tropes": [
            ("Dark Academia", 0.85),
            ("Anti-Hero", 0.85),
            ("Political Intrigue", 0.65),
            ("Magic System", 0.65),
            ("Tournament/Competition", 0.45),
        ],
        "archetypes": [
            ("The Shadow", 9), ("The Trickster", 8), ("The Ruler", 7), ("The Sage", 6),
        ],
    },
    {
        "title": "If We Were Villains",
        "author": "M.L. Rio",
        "isbn": "978-1-250-09587-1",
        "pub_date": "2017-04-11",
        "description": (
            "Oliver Marks has served ten years in jail for a murder he may or may not have "
            "committed. Released, he finally tells the story of his senior year at Dellecher "
            "Classical Conservatory — where seven students lived and breathed Shakespeare's "
            "tragedies so completely that the line between fiction and reality dissolved, "
            "with fatal consequences."
        ),
        "genres": ["Mystery"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Dark Academia", 0.85),
            ("Unreliable Narrator", 0.85),
            ("Tragedy", 0.65),
            ("Secret Identity", 0.25),
        ],
        "archetypes": [("The Tragic Hero", 9), ("The Shadow", 8), ("The Outcast", 7)],
    },
    {
        "title": "Jonathan Strange & Mr Norrell",
        "author": "Susanna Clarke",
        "isbn": "978-1-59606-106-0",
        "pub_date": "2004-09-08",
        "description": (
            "In early nineteenth-century England, two very different magicians emerge to "
            "restore English magic. The reclusive Mr Norrell hoards his knowledge jealously, "
            "while the daring Jonathan Strange pushes the boundaries of what is possible. "
            "Their rivalry threatens not only their lives but England itself. A magnificent "
            "work of historical fantasy with a distinctive dark wit."
        ),
        "genres": ["Fantasy", "Historical Fiction"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Magic System", 0.85),
            ("Political Intrigue", 0.65),
            ("Hidden World", 0.45),
            ("Enemies to Lovers", 0.10),
        ],
        "archetypes": [
            ("The Sage", 9), ("The Rebel", 8), ("The Mentor", 7), ("The Ruler", 5),
        ],
    },
    {
        "title": "Piranesi",
        "author": "Susanna Clarke",
        "isbn": "978-1-63557-563-1",
        "pub_date": "2020-09-15",
        "description": (
            "Piranesi lives in the House — an infinite structure of halls, statues, and "
            "tides. He is content and studies its mysteries. But when cryptic messages begin "
            "to appear, he must question the nature of the House, the only other person he "
            "knows, and ultimately himself. An eerie, utterly original mystery about identity "
            "and the nature of reality."
        ),
        "genres": ["Fantasy", "Mystery"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Hidden World", 0.85),
            ("Unreliable Narrator", 0.85),
            ("Secret Identity", 0.85),
            ("Magic System", 0.25),
        ],
        "archetypes": [("The Explorer", 9), ("The Outcast", 9), ("The Sage", 6)],
    },
    {
        "title": "The Hunger Games",
        "author": "Suzanne Collins",
        "isbn": "978-0-439-02348-1",
        "pub_date": "2008-09-14",
        "description": (
            "In the ruins of North America, the totalitarian Capitol forces each of its "
            "twelve districts to send two teenagers to compete in the Hunger Games — a "
            "televised fight to the death. When sixteen-year-old Katniss Everdeen volunteers "
            "to take her sister's place, she enters an arena where survival means defying "
            "an entire government."
        ),
        "genres": ["Science Fiction"],
        "book_types": ["Novel", "YA", "Series Starter"],
        "tropes": [
            ("Tournament/Competition", 0.85),
            ("Political Intrigue", 0.85),
            ("Chosen One", 0.65),
            ("Coming of Age", 0.65),
            ("Forbidden Love", 0.25),
        ],
        "archetypes": [("The Hero", 9), ("The Rebel", 9), ("The Caregiver", 7)],
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "isbn": "978-0-14-143951-8",
        "pub_date": "1813-01-28",
        "description": (
            "The Bennet family's precarious future rests on the marriages of its five daughters. "
            "Witty and independent Elizabeth Bennet meets the proud and wealthy Mr Darcy, "
            "and their antagonism slowly transforms — through misunderstandings and hard-won "
            "self-knowledge — into one of literature's most celebrated love stories. Austen's "
            "sharpest social satire and most beloved novel."
        ),
        "genres": ["Classic", "Romance"],
        "book_types": ["Novel", "Standalone"],
        "tropes": [
            ("Enemies to Lovers", 0.85),
            ("Slow Burn Romance", 0.65),
            ("Political Intrigue", 0.25),
        ],
        "archetypes": [("The Rebel", 8), ("The Lover", 9), ("The Trickster", 5)],
    },
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "isbn": "978-0-618-00221-3",
        "pub_date": "1937-09-21",
        "description": (
            "Bilbo Baggins is a comfortable, unambitious hobbit whose quiet life is upended "
            "when a wizard and thirteen dwarves arrive and sweep him into an adventure. "
            "From the misty mountains to the lair of the dragon Smaug, Bilbo must rely on "
            "unexpected reserves of cunning and courage. The book that introduced Middle-earth "
            "to the world — a timeless tale of the unlikely hero."
        ),
        "genres": ["Fantasy"],
        "book_types": ["Novel", "Standalone"],
        "tropes": [
            ("Coming of Age", 0.65),
            ("Found Family", 0.65),
            ("Hidden World", 0.45),
            ("Chosen One", 0.45),
        ],
        "archetypes": [
            ("The Explorer", 9), ("The Hero", 8), ("The Mentor", 7), ("The Trickster", 5),
        ],
    },
    {
        "title": "Gone Girl",
        "author": "Gillian Flynn",
        "isbn": "978-0-307-58836-4",
        "pub_date": "2012-06-05",
        "description": (
            "On the morning of their fifth wedding anniversary, Nick Dunne's wife Amy "
            "disappears. The police and media make Nick their prime suspect — but Amy's "
            "diary tells a very different story. Told in alternating perspectives, Gone Girl "
            "is a diabolically clever thriller about the lies we tell in marriage and the "
            "performances we give the world."
        ),
        "genres": ["Thriller", "Mystery"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Unreliable Narrator", 1.0),
            ("Secret Identity", 0.85),
            ("Revenge", 0.65),
        ],
        "archetypes": [("The Shadow", 10), ("The Trickster", 9), ("The Outcast", 5)],
    },
    {
        "title": "The Night Circus",
        "author": "Erin Morgenstern",
        "isbn": "978-0-385-53463-5",
        "pub_date": "2011-09-13",
        "description": (
            "The circus arrives without warning — a sea of black and white striped tents "
            "that appears overnight and vanishes just as mysteriously. Inside are wonders "
            "that seem to defy the laws of nature. Behind the scenes, two young magicians "
            "are locked in a competition set by their rival teachers, a contest in which "
            "only one can survive."
        ),
        "genres": ["Fantasy", "Romance"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Magic System", 0.85),
            ("Forbidden Love", 0.65),
            ("Slow Burn Romance", 0.65),
            ("Tournament/Competition", 0.45),
        ],
        "archetypes": [("The Lover", 9), ("The Trickster", 8), ("The Shadow", 6)],
    },
    {
        "title": "Six of Crows",
        "author": "Leigh Bardugo",
        "isbn": "978-1-62779-432-2",
        "pub_date": "2015-09-29",
        "description": (
            "Criminal prodigy Kaz Brekker is offered an impossible heist that could make "
            "him wealthy beyond dreams — or get him killed. He assembles a crew of six "
            "dangerous outcasts to break into the most impenetrable prison in the world "
            "and steal an invention that could change the balance of power forever. "
            "A heist fantasy built on found family, sharp wit, and moral ambiguity."
        ),
        "genres": ["Fantasy"],
        "book_types": ["Novel", "YA", "Series Starter"],
        "tropes": [
            ("The Heist", 0.85),
            ("Found Family", 0.85),
            ("Anti-Hero", 0.65),
            ("Political Intrigue", 0.45),
            ("Slow Burn Romance", 0.25),
        ],
        "archetypes": [
            ("The Trickster", 9), ("The Rebel", 8), ("The Outcast", 7), ("The Caregiver", 6),
        ],
    },
    {
        "title": "The Secret History",
        "author": "Donna Tartt",
        "isbn": "978-1-101-97321-2",
        "pub_date": "1992-09-16",
        "description": (
            "Richard Papen arrives at Hampden College and falls in with a small, closed "
            "group of classics students under the spell of their charismatic professor. "
            "Their immersion in ancient beauty and Dionysian ideals leads them to commit "
            "a terrible act — and then another. Told in reverse from the moment of the "
            "crime, this is a dark, unflinching study of guilt, obsession, and complicity."
        ),
        "genres": ["Mystery"],
        "book_types": ["Novel", "Adult", "Standalone"],
        "tropes": [
            ("Dark Academia", 1.0),
            ("Unreliable Narrator", 0.85),
            ("Tragedy", 0.65),
            ("Revenge", 0.25),
        ],
        "archetypes": [
            ("The Shadow", 9), ("The Outcast", 8), ("The Sage", 7), ("The Tragic Hero", 8),
        ],
    },
]


async def get_or_create_author(db, name: str) -> Author:
    result = await db.execute(select(Author).where(Author.name == name))
    author = result.scalar_one_or_none()
    if not author:
        author = Author(name=name)
        db.add(author)
        await db.flush()
    return author


async def main() -> None:
    print("Clearing existing data…")
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "TRUNCATE TABLE book_ratings, book_tropes, character_dna, "
            "book_genres, book_book_types, book_tones, books, authors, tropes, "
            "archetypes, genres, book_types, tones RESTART IDENTITY CASCADE"
        ))
        await db.commit()

    print("Seeding genres…")
    async with AsyncSessionLocal() as db:
        for g in GENRES:
            db.add(Genre(**g))
        await db.commit()

    print("Seeding book types…")
    async with AsyncSessionLocal() as db:
        for bt in BOOK_TYPES:
            db.add(BookType(**bt))
        await db.commit()

    print("Seeding tones…")
    async with AsyncSessionLocal() as db:
        for name in TONES:
            db.add(Tone(name=name))
        await db.commit()

    print("Seeding tropes…")
    async with AsyncSessionLocal() as db:
        for category, trope_list in TROPES.items():
            for name, description in trope_list:
                db.add(Trope(name=name, description=description, category=category))
        await db.commit()

    print("Seeding archetypes…")
    async with AsyncSessionLocal() as db:
        for name, description in ARCHETYPES:
            db.add(Archetype(name=name, description=description))
        await db.commit()

    print(f"Seeding {len(BOOKS)} books…")
    book_ids = []
    for book_data in BOOKS:
        async with AsyncSessionLocal() as db:
            author = await get_or_create_author(db, book_data["author"])
            pub = date.fromisoformat(book_data["pub_date"])
            book = Book(
                title=book_data["title"],
                author_id=author.author_id,
                isbn=book_data["isbn"],
                publication_date=pub,
                description=book_data["description"],
            )
            db.add(book)
            await db.flush()

            for trope_name, weight in book_data["tropes"]:
                result = await db.execute(select(Trope).where(Trope.name == trope_name))
                trope = result.scalar_one()
                db.add(BookTrope(book_id=book.book_id, trope_id=trope.trope_id, weight=weight))

            for arch_name, importance in book_data["archetypes"]:
                result = await db.execute(select(Archetype).where(Archetype.name == arch_name))
                archetype = result.scalar_one()
                db.add(CharacterDNA(
                    book_id=book.book_id,
                    archetype_id=archetype.archetype_id,
                    importance=importance,
                ))

            await db.commit()
            await db.refresh(book)

            for genre_name in book_data["genres"]:
                result = await db.execute(select(Genre).where(Genre.name == genre_name))
                genre = result.scalar_one()
                await db.execute(
                    pg_insert(book_genres)
                    .values(book_id=book.book_id, genre_id=genre.genre_id)
                    .on_conflict_do_nothing()
                )

            for bt_name in book_data["book_types"]:
                result = await db.execute(select(BookType).where(BookType.name == bt_name))
                bt = result.scalar_one()
                await db.execute(
                    pg_insert(book_book_types)
                    .values(book_id=book.book_id, book_type_id=bt.book_type_id)
                    .on_conflict_do_nothing()
                )

            await db.commit()
            book_ids.append(book.book_id)
            print(f"  [{book.book_id}] {book.title}")

    print(f"\nEmbedding {len(book_ids)} books…")
    for book_id in book_ids:
        async with AsyncSessionLocal() as db:
            book = await embed_book(book_id, db)
            print(f"  [{book.book_id}] {book.title} — embedded")

    print(f"\nDone. Seeded {len(book_ids)} books.")


if __name__ == "__main__":
    asyncio.run(main())
