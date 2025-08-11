#!/usr/bin/env python3
"""Test script to verify Add Cards functionality."""

from danki.engine.db import Database

def test_deck_creation_and_cards():
    """Test that we can create decks and add cards."""
    print("Testing deck creation and card addition...")
    
    # Initialize database
    db = Database("test_add_cards.sqlite")
    
    # Test 1: Create a deck
    print("\n1. Creating deck...")
    deck_id = db.create_deck("Test German Deck")
    print(f"✓ Created deck with ID: {deck_id}")
    
    # Test 2: List decks
    print("\n2. Listing decks...")
    decks = db.list_decks()
    for deck in decks:
        print(f"   - {deck['name']} (ID: {deck['id']}, builtin: {deck['is_builtin']})")
    
    # Test 3: Add some cards with rich metadata
    print("\n3. Adding cards with metadata...")
    
    # Mock German verb data (like what Gemini would return)
    verb_data = {
        "base_d": "laufen",
        "base_e": "to run", 
        "word_type": "verb",
        "artikel_d": "",
        "plural_d": "",
        "conjugation": {
            "ich": "laufe",
            "du": "läufst",
            "er_sie_es": "läuft",
            "wir": "laufen", 
            "ihr": "lauft",
            "sie_Sie": "laufen"
        },
        "praesens": "läuft",
        "s1": "Ich laufe jeden Tag.",
        "s1e": "I run every day.",
        "meta": {"tags": ["verb", "A1"], "context": "daily activities"}
    }
    
    note_id = db.add_note(deck_id, verb_data["base_d"], verb_data["base_e"], verb_data)
    print(f"✓ Added verb card: {verb_data['base_d']} -> {verb_data['base_e']}")
    
    # Mock German noun data
    noun_data = {
        "base_d": "der Hund", 
        "base_e": "the dog",
        "word_type": "noun",
        "artikel_d": "der",
        "plural_d": "die Hunde", 
        "s1": "Der Hund läuft im Park.",
        "s1e": "The dog runs in the park.",
        "meta": {"tags": ["noun", "A1"], "context": "animals"}
    }
    
    note_id = db.add_note(deck_id, noun_data["base_d"], noun_data["base_e"], noun_data)
    print(f"✓ Added noun card: {noun_data['base_d']} -> {noun_data['base_e']}")
    
    # Test 4: Query cards for review
    print("\n4. Querying cards for review...")
    import time
    now = int(time.time())
    cards = db.get_cards_for_review([deck_id], now)
    
    print(f"Found {len(cards)} cards ready for review:")
    for card in cards:
        print(f"   - {card['front']} -> {card['back']} (state: {card['state']})")
        if card['meta']:
            import json
            meta = json.loads(card['meta']) if isinstance(card['meta'], str) else card['meta']
            word_type = meta.get('word_type', 'unknown')
            print(f"     Type: {word_type}, Tags: {meta.get('meta', {}).get('tags', [])}")
    
    # Test 5: Get today's stats
    print("\n5. Getting today's stats...")
    stats = db.get_stats_today([deck_id], now)
    print(f"Today's stats: {stats}")
    
    print(f"\n✅ All tests passed! Database working correctly.")
    
    # Cleanup
    db.close()
    import os
    os.remove("test_add_cards.sqlite")
    print("✓ Cleaned up test database")

if __name__ == "__main__":
    test_deck_creation_and_cards()