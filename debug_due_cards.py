#!/usr/bin/env python3
"""Debug why no cards are showing in session."""

from danki.engine.db import Database
import time

def debug_due_cards():
    """Debug card due times and daily limits."""
    db = Database("danki_data.sqlite")
    
    now_ts = int(time.time())
    
    print(f"🕒 Current time: {now_ts} ({time.ctime(now_ts)})")
    print("\n" + "=" * 80)
    
    # Get all cards with their due times
    cards = db.conn.execute("""
        SELECT c.*, n.front, n.back, d.name as deck_name
        FROM cards c
        JOIN notes n ON c.note_id = n.id  
        JOIN decks d ON n.deck_id = d.id
        ORDER BY c.due_ts
    """).fetchall()
    
    print(f"📇 All cards in database ({len(cards)} total):")
    
    for i, card in enumerate(cards, 1):
        due_ts = card['due_ts']
        is_due = due_ts <= now_ts
        time_diff = due_ts - now_ts
        
        print(f"\n📋 Card {i}:")
        print(f"  Template: {card['template']}")
        print(f"  Front: '{card['front']}'")
        print(f"  Back: '{card['back']}'")
        print(f"  State: {card['state']}")
        print(f"  Due: {due_ts} ({time.ctime(due_ts)})")
        print(f"  Due now? {'✅ YES' if is_due else '❌ NO'}")
        
        if not is_due:
            if time_diff < 60:
                print(f"  Due in: {time_diff} seconds")
            elif time_diff < 3600:
                print(f"  Due in: {time_diff//60} minutes")
            else:
                print(f"  Due in: {time_diff//3600} hours")
    
    # Check daily stats
    print(f"\n📊 Daily Stats:")
    decks = db.list_decks()
    
    from danki.utils.study_time import study_time
    study_date = study_time.get_study_date(now_ts)
    
    for deck in decks:
        deck_id = deck['id']
        prefs = db.get_deck_preferences(deck_id)
        daily_stats = db.get_daily_stats(deck_id, study_date)
        
        print(f"  📚 {deck['name']}:")
        print(f"    Limits: {prefs.get('new_per_day', 0)} new, {prefs.get('rev_per_day', 0)} review")
        print(f"    Today: {daily_stats['new_studied']} new, {daily_stats['rev_studied']} review")

if __name__ == "__main__":
    debug_due_cards()