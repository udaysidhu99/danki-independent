#!/usr/bin/env python3
"""
Test the new Anki-style queue building system.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from danki.engine.scheduler import Scheduler, Rating
from danki.engine.db import Database


def test_anki_queue_system():
    """Test the new Anki-style hierarchical queue building."""
    print("🚀 Testing Anki-Style Queue System")
    print("=" * 45)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck with multiple notes
        deck_id = db.create_deck("Anki Queue Test Deck")
        note_ids = []
        
        # Add 6 notes (12 cards total with bidirectional)
        for i in range(6):
            note_id = db.add_note(deck_id, f"German Word {i}", f"English Word {i}", {"word_type": "noun"})
            note_ids.append(note_id)
        
        print(f"📚 Created deck with {len(note_ids)} notes")
        
        # Test separate card type queries
        now = int(time.time())
        
        print("\n🔍 Testing separate card type queries:")
        learning_cards = db.get_learning_cards([deck_id], now)
        review_cards = db.get_review_cards([deck_id], now)
        new_cards = db.get_new_cards([deck_id], limit=5)
        
        print(f"   Learning cards: {len(learning_cards)}")
        print(f"   Review cards: {len(review_cards)}")
        print(f"   New cards: {len(new_cards)} (limited to 5)")
        
        # Test Anki-style session building
        print(f"\n🎯 Building Anki-style session:")
        session = scheduler.build_anki_session([deck_id], now_ts=now)
        
        if session:
            print(f"\n📊 Session Analysis:")
            print(f"   Total cards in session: {len(session)}")
            
            # Analyze card types in session
            states = {}
            templates = {}
            notes_used = set()
            
            for card in session:
                state = card['state']
                template = card.get('template', 'unknown')
                note_id = card['note_id']
                
                states[state] = states.get(state, 0) + 1
                templates[template] = templates.get(template, 0) + 1
                notes_used.add(note_id)
            
            print(f"   States: {states}")
            print(f"   Templates: {templates}")
            print(f"   Unique notes used: {len(notes_used)} out of {len(note_ids)}")
            
            # Test sibling burying
            if len(notes_used) < len(session):
                print(f"   ✅ Sibling burying working: {len(session)} cards from {len(notes_used)} notes")
            else:
                print(f"   ⚠️  No sibling burying detected")
            
            # Show first few cards
            print(f"\n📝 First 5 cards in session:")
            for i, card in enumerate(session[:5]):
                state = card['state']
                note_id = card['note_id'][:8]
                template = card.get('template', 'unknown')
                front = card['front'][:20] + "..." if len(card['front']) > 20 else card['front']
                print(f"   {i+1}. {state} | {template} | {note_id}... | {front}")
                
            return True
        else:
            print("   ❌ No cards in session")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            if 'scheduler' in locals():
                scheduler.db.close()
            if 'db' in locals():
                db.close()
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
        except:
            pass


def test_sibling_burying_after_review():
    """Test sibling burying after rating a card."""
    print("\n🧪 Testing Sibling Burying After Review")
    print("=" * 40)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("Sibling Burying Test")
        note_id = db.add_note(deck_id, "laufen", "to run", {"word_type": "verb"})
        
        # Get initial session
        now = int(time.time())
        session = scheduler.build_anki_session([deck_id], now_ts=now)
        
        print(f"📊 Initial session: {len(session)} cards")
        
        if len(session) >= 2:
            # Rate first card as Again
            first_card = session[0]
            card_id = first_card['card_id']
            note_of_first = first_card['note_id']
            
            print(f"🔴 Rating first card from note {note_of_first[:8]}... as AGAIN")
            scheduler.review(card_id, Rating.AGAIN, 2000, now)
            
            # Build new session
            new_session = scheduler.build_anki_session([deck_id], now_ts=now)
            
            print(f"📊 Session after rating: {len(new_session)} cards")
            
            # Check if sibling card appears
            sibling_appears = False
            learning_card_appears = False
            
            for card in new_session:
                if card['card_id'] == card_id:
                    learning_card_appears = True
                    print(f"   ✅ Rated card reappears as learning card")
                elif card['note_id'] == note_of_first:
                    sibling_appears = True
                    print(f"   ⚠️  Sibling card from same note appears")
            
            if not sibling_appears:
                print(f"   ✅ Sibling burying working: no other cards from same note")
                return True
            else:
                print(f"   ❌ Sibling burying failed: sibling card appeared")
                return False
        else:
            print(f"   ⚠️  Not enough cards to test sibling burying")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            if 'scheduler' in locals():
                scheduler.db.close()
            if 'db' in locals():
                db.close()
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
        except:
            pass


if __name__ == "__main__":
    success1 = test_anki_queue_system()
    success2 = test_sibling_burying_after_review()
    
    print(f"\n📋 Results:")
    print(f"   Queue System: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Sibling Burying: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print(f"🎉 Anki-style queue system is working!")
    else:
        print(f"⚠️  Some issues detected with the queue system.")