

# cli_test.py
from danki.engine.db import Database

if __name__ == "__main__":
    db = Database("test.sqlite")
    deck_path = "danki/data/decks/a1.sample.jsonl"  # adjust path if needed

    try:
        cards = db.load_deck_from_jsonl(deck_path)
        print(f"Loaded {len(cards)} cards:")
        for c in cards:
            print(f" - {c['front']} -> {c['back']}")
    except FileNotFoundError as e:
        print(e)