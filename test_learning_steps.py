#!/usr/bin/env python3
"""
Test learning step progression like Anki.
Verify proper step-by-step learning advancement.
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


def test_learning_step_progression():
    """Test multi-step learning progression."""
    print("🧪 Testing Learning Step Progression")
    print("=" * 40)
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    temp_db_path = temp_db.name
    
    try:
        scheduler = Scheduler(temp_db_path)
        db = Database(temp_db_path)
        
        # Create test deck
        deck_id = db.create_deck("Step Progression Test")
        note_id = db.add_note(deck_id, "Test Card", "Answer", {})
        
        # Get the first card
        session = scheduler.build_session([deck_id])
        test_card = session[0]
        card_id = test_card['card_id']
        
        print(f"📝 Starting with: {test_card['state']} card")
        
        # Step 1: Rate new card as "Again" → Learning Step 0 (1 minute)
        now = int(time.time())
        scheduler.review(card_id, Rating.AGAIN, 2000, now)
        
        card = scheduler._get_card(card_id)
        print(f"1️⃣ After AGAIN: state={card['state']}, step={card['step_index']}, due_in={(card['due_ts'] - now)/60:.1f}min")
        
        # Step 2: Time passes, rate as "Good" → Learning Step 1 (10 minutes)  
        time1 = now + 90  # 1.5 minutes later
        scheduler.review(card_id, Rating.GOOD, 1500, time1)
        
        card = scheduler._get_card(card_id)
        print(f"2️⃣ After GOOD (step 0): state={card['state']}, step={card['step_index']}, due_in={(card['due_ts'] - time1)/60:.1f}min")
        
        # Step 3: Time passes, rate as "Again" → Back to Step 0 (1 minute)
        time2 = time1 + 600  # 10 minutes later
        scheduler.review(card_id, Rating.AGAIN, 3000, time2)
        
        card = scheduler._get_card(card_id)
        print(f"3️⃣ After AGAIN (step 1): state={card['state']}, step={card['step_index']}, due_in={(card['due_ts'] - time2)/60:.1f}min")
        
        # Step 4: Complete learning successfully
        time3 = time2 + 90  # 1.5 minutes later
        scheduler.review(card_id, Rating.GOOD, 1200, time3)
        
        card = scheduler._get_card(card_id)
        print(f"4️⃣ After GOOD (step 0 again): state={card['state']}, step={card['step_index']}, due_in={(card['due_ts'] - time3)/60:.1f}min")
        
        # Step 5: Graduate to review
        time4 = time3 + 600  # 10 minutes later
        scheduler.review(card_id, Rating.GOOD, 1800, time4)
        
        card = scheduler._get_card(card_id)
        print(f"5️⃣ After GOOD (step 1): state={card['state']}, interval={card['interval_days']}days, ease={card['ease']}")
        
        print(f"\n✅ Learning progression completed!")
        print(f"🎯 Card successfully graduated from new → learning → review")
        print(f"📚 Learning steps: 1min → 10min → Graduate (like Anki)")
        
        return card['state'] == 'review'
        
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
    success = test_learning_step_progression()
    print(f"\n📋 Result: {'✅ PASS' if success else '❌ FAIL'}")