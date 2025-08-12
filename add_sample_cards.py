#!/usr/bin/env python3
"""Add sample German vocabulary cards to test the daily limit system."""

from danki.engine.db import Database
import time

def add_sample_cards():
    """Add sample German vocabulary cards."""
    db = Database("danki_data.sqlite")
    
    # Create or get a test deck
    decks = db.list_decks()
    test_deck = None
    for deck in decks:
        if deck['name'] == 'German Basics':
            test_deck = deck
            break
    
    if not test_deck:
        deck_id = db.create_deck('German Basics', False, {
            "new_per_day": 5,  # Lower limit for testing
            "rev_per_day": 20,
            "steps_min": [10, 1440]
        })
        print(f"Created deck: German Basics")
    else:
        deck_id = test_deck['id']
        print(f"Using existing deck: German Basics")
    
    # Sample German vocabulary with rich metadata
    sample_cards = [
        {
            "front": "der Hund",
            "back": "the dog",
            "meta": {
                "artikel_d": "der",
                "plural_d": "die Hunde",
                "word_type": "noun",
                "s1": "Der Hund bellt laut.",
                "s1e": "The dog barks loudly.",
                "s2": "Mein Hund ist sehr freundlich.",
                "s2e": "My dog is very friendly."
            }
        },
        {
            "front": "essen",
            "back": "to eat",
            "meta": {
                "word_type": "verb",
                "conjugation": {
                    "ich": "esse",
                    "du": "isst", 
                    "er_sie_es": "isst",
                    "wir": "essen",
                    "ihr": "esst",
                    "sie_Sie": "essen"
                },
                "praeteritum": "aß",
                "perfekt": "hat gegessen",
                "s1": "Ich esse gern Pizza.",
                "s1e": "I like to eat pizza.",
                "s2": "Er isst jeden Tag Salat.",
                "s2e": "He eats salad every day."
            }
        },
        {
            "front": "das Haus",
            "back": "the house",
            "meta": {
                "artikel_d": "das",
                "plural_d": "die Häuser",
                "word_type": "noun",
                "s1": "Das Haus ist sehr groß.",
                "s1e": "The house is very big.",
                "s2": "Wir kaufen ein neues Haus.",
                "s2e": "We are buying a new house."
            }
        },
        {
            "front": "sprechen",
            "back": "to speak",
            "meta": {
                "word_type": "verb",
                "conjugation": {
                    "ich": "spreche",
                    "du": "sprichst",
                    "er_sie_es": "spricht", 
                    "wir": "sprechen",
                    "ihr": "sprecht",
                    "sie_Sie": "sprechen"
                },
                "praeteritum": "sprach",
                "perfekt": "hat gesprochen",
                "s1": "Sie spricht drei Sprachen.",
                "s1e": "She speaks three languages.",
                "s2": "Können Sie Deutsch sprechen?",
                "s2e": "Can you speak German?"
            }
        },
        {
            "front": "die Katze",
            "back": "the cat",
            "meta": {
                "artikel_d": "die",
                "plural_d": "die Katzen",
                "word_type": "noun",
                "s1": "Die Katze schläft auf dem Sofa.",
                "s1e": "The cat sleeps on the sofa.",
                "s2": "Unsere Katze ist sehr süß.",
                "s2e": "Our cat is very cute."
            }
        },
        {
            "front": "lernen",
            "back": "to learn",
            "meta": {
                "word_type": "verb",
                "conjugation": {
                    "ich": "lerne",
                    "du": "lernst",
                    "er_sie_es": "lernt",
                    "wir": "lernen", 
                    "ihr": "lernt",
                    "sie_Sie": "lernen"
                },
                "praeteritum": "lernte",
                "perfekt": "hat gelernt",
                "s1": "Ich lerne Deutsch.",
                "s1e": "I am learning German.",
                "s2": "Sie lernt sehr schnell.",
                "s2e": "She learns very quickly."
            }
        },
        {
            "front": "das Wasser",
            "back": "the water",
            "meta": {
                "artikel_d": "das",
                "plural_d": "",  # Uncountable
                "word_type": "noun", 
                "s1": "Das Wasser ist kalt.",
                "s1e": "The water is cold.",
                "s2": "Ich trinke viel Wasser.",
                "s2e": "I drink a lot of water."
            }
        },
        {
            "front": "gehen",
            "back": "to go",
            "meta": {
                "word_type": "verb",
                "conjugation": {
                    "ich": "gehe",
                    "du": "gehst",
                    "er_sie_es": "geht",
                    "wir": "gehen",
                    "ihr": "geht", 
                    "sie_Sie": "gehen"
                },
                "praeteritum": "ging",
                "perfekt": "ist gegangen",
                "s1": "Wir gehen ins Kino.",
                "s1e": "We are going to the cinema.",
                "s2": "Er geht jeden Tag zur Arbeit.",
                "s2e": "He goes to work every day."
            }
        },
        {
            "front": "die Zeit",
            "back": "the time",
            "meta": {
                "artikel_d": "die",
                "plural_d": "die Zeiten",
                "word_type": "noun",
                "s1": "Wir haben keine Zeit.",
                "s1e": "We don't have time.",
                "s2": "Die Zeit vergeht schnell.",
                "s2e": "Time passes quickly."
            }
        },
        {
            "front": "schön",
            "back": "beautiful",
            "meta": {
                "word_type": "adjective",
                "s1": "Das ist ein schönes Bild.",
                "s1e": "That is a beautiful picture.",
                "s2": "Heute ist schönes Wetter.",
                "s2e": "Today is beautiful weather."
            }
        }
    ]
    
    # Add cards to database
    added_count = 0
    for card_data in sample_cards:
        try:
            note_id = db.add_note(
                deck_id=deck_id,
                front=card_data["front"],
                back=card_data["back"], 
                meta=card_data["meta"]
            )
            added_count += 1
            print(f"✓ Added: {card_data['front']} → {card_data['back']}")
        except Exception as e:
            print(f"✗ Failed to add {card_data['front']}: {e}")
    
    print(f"\nSuccessfully added {added_count}/{len(sample_cards)} cards to 'German Basics' deck!")
    print(f"Daily limits: {db.get_deck_preferences(deck_id)}")
    
    # Show deck stats
    import time
    now_ts = int(time.time())
    stats = db.get_stats_today([deck_id], now_ts)
    print(f"Cards available: {stats}")

if __name__ == "__main__":
    add_sample_cards()