#!/usr/bin/env python3
"""Simple test to check if Add Cards processing works."""

from danki.engine.db import Database

def test_ui_integration():
    """Test the integration path that the UI would use."""
    print("Testing UI integration path...")
    
    # Step 1: Initialize database (like MainWindow does)
    db = Database("test_ui.sqlite")
    print("✓ Database initialized")
    
    # Step 2: Simulate deck creation (like AddCardsScreen.ensure_deck_exists)
    deck_name = "My Test Deck"
    
    # Check if deck exists
    decks = db.list_decks()
    existing_deck = None
    for deck in decks:
        if deck['name'] == deck_name:
            existing_deck = deck['id']
            break
    
    if not existing_deck:
        deck_id = db.create_deck(deck_name)
        print(f"✓ Created new deck: {deck_name} (ID: {deck_id})")
    else:
        deck_id = existing_deck
        print(f"✓ Using existing deck: {deck_name} (ID: {deck_id})")
    
    # Step 3: Simulate word processing (like GeminiWorker would do)
    words = ["laufen", "sprechen", "der Hund"]
    print(f"\\nProcessing {len(words)} words...")
    
    success_count = 0
    for word in words:
        # Mock Gemini response (this is what's in GeminiWorker.query_gemini_api)
        if word.endswith(("en", "ern", "eln")):
            # Verb
            mock_data = {
                "base_d": word,
                "base_e": f"[translation of {word}]",
                "word_type": "verb",
                "artikel_d": "",
                "plural_d": "",
                "conjugation": {
                    "ich": word[:-2] + "e",
                    "du": word[:-2] + "st", 
                    "er_sie_es": word[:-2] + "t",
                    "wir": word,
                    "ihr": word[:-2] + "t",
                    "sie_Sie": word
                },
                "s1": f"Ich {word} jeden Tag.",
                "s1e": f"I {word[:-2]} every day."
            }
        else:
            # Noun
            mock_data = {
                "base_d": word,
                "base_e": f"[translation of {word}]",
                "artikel_d": "der" if word.endswith("er") else "die" if word.endswith("e") else "das",
                "word_type": "noun",
                "s1": f"Das ist {word}.",
                "s1e": f"This is {word}.",
            }
        
        # Add to database (like AddCardsScreen.on_word_processed does)
        try:
            note_id = db.add_note(
                deck_id=deck_id,
                front=mock_data.get('base_d', word),
                back=mock_data.get('base_e', '[translation]'),
                meta=mock_data
            )
            print(f"✓ Added: {word} -> {mock_data.get('base_e', '[translation]')}")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to add {word}: {e}")
    
    print(f"\\n✅ Successfully processed {success_count}/{len(words)} words")
    
    # Step 4: Verify cards are in database
    import time
    cards = db.get_cards_for_review([deck_id], int(time.time()))
    print(f"✓ Found {len(cards)} cards in database ready for review")
    
    # Cleanup
    db.close()
    import os
    os.remove("test_ui.sqlite")
    print("✓ Test complete")

if __name__ == "__main__":
    test_ui_integration()