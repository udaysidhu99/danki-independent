# Anki-Style Queue Implementation Plan

Based on analysis of Anki's proven approach, here's the plan to rewrite our session management to match their architecture.

## Phase 1: Separate Queue Building

### 1.1 Database Layer Updates
**File**: `danki/engine/db.py`

```python
def get_learning_cards(self, deck_ids: List[str], now_ts: int) -> List[Dict]:
    """Get learning cards due now or within session timeframe."""
    
def get_review_cards(self, deck_ids: List[str], now_ts: int, limit: int) -> List[Dict]:
    """Get review cards due for today."""
    
def get_new_cards(self, deck_ids: List[str], limit: int) -> List[Dict]:
    """Get new cards up to daily limit."""
```

### 1.2 Scheduler Queue Building
**File**: `danki/engine/scheduler.py`

```python
def build_anki_session(self, deck_ids: List[str], now_ts: int) -> List[Dict]:
    """Build session using Anki's hierarchical approach."""
    # 1. Gather learning cards (time-critical)
    learning_cards = self.db.get_learning_cards(deck_ids, now_ts)
    
    # 2. Gather review cards
    review_cards = self.db.get_review_cards(deck_ids, now_ts, review_limit)
    
    # 3. Gather new cards  
    new_cards = self.db.get_new_cards(deck_ids, new_limit)
    
    # 4. Apply sibling burying during collection
    filtered_cards = self._apply_sibling_burying(learning_cards, review_cards, new_cards)
    
    # 5. Add fuzzing to prevent clustering
    fuzzed_cards = self._apply_anti_clustering_fuzz(filtered_cards)
    
    # 6. Merge with proper interleaving
    return self._interleave_card_types(fuzzed_cards)
```

## Phase 2: Sibling Burying System

### 2.1 Burying Logic
```python
def _apply_sibling_burying(self, learning_cards, review_cards, new_cards):
    """Apply Anki's sibling burying rules."""
    buried_notes = set()
    
    # Learning cards can bury siblings in review/new
    for card in learning_cards:
        if card['note_id'] not in buried_notes:
            self._bury_siblings(card['note_id'], review_cards, new_cards)
            buried_notes.add(card['note_id'])
    
    # Review cards can bury siblings in new cards
    for card in review_cards:
        if card['note_id'] not in buried_notes:
            self._bury_siblings(card['note_id'], new_cards)
            buried_notes.add(card['note_id'])
            
    return self._filter_buried_cards(learning_cards, review_cards, new_cards)
```

## Phase 3: Anti-Clustering & Fuzzing

### 3.1 Fuzzing Implementation
```python
def _apply_anti_clustering_fuzz(self, cards):
    """Add small random delays to prevent clustering."""
    for card in cards:
        if card['state'] == 'learning':
            # Up to 5 minutes random delay for learning cards
            fuzz = random.randint(0, 300)  # 0-300 seconds
            card['display_delay'] = fuzz
    
    return sorted(cards, key=lambda c: c.get('display_delay', 0))
```

## Phase 4: Dynamic Queue Management

### 4.1 State Transition Handling
```python
def handle_card_rating(self, card_id: str, rating: Rating):
    """Handle card rating with proper queue updates."""
    # 1. Update card state using SM-2+
    self.review_card(card_id, rating)
    
    # 2. Check if card transitioned to learning
    updated_card = self._get_card(card_id)
    
    # 3. If now learning, insert into learning queue with fuzzing
    if updated_card['state'] == 'learning':
        fuzzed_due = self._apply_learning_fuzz(updated_card['due_ts'])
        self._insert_into_learning_queue(updated_card, fuzzed_due)
    
    # 4. Rebuild queue if needed (less frequent than current approach)
    if self._should_rebuild_queue():
        self.session_queue = self.build_anki_session(self.current_deck_ids, int(time.time()))
```

## Implementation Priority

1. **High Priority** - Phase 1: Separate queue building
2. **High Priority** - Phase 2: Sibling burying (fixes immediate repetition)  
3. **Medium Priority** - Phase 3: Anti-clustering fuzzing
4. **Medium Priority** - Phase 4: Dynamic queue optimization

## Benefits of This Approach

1. **Proven Reliability**: Matches Anki's battle-tested system
2. **Proper Sibling Handling**: Native burying instead of reactive filtering
3. **Scientific Spacing**: Anti-clustering improves learning outcomes
4. **Performance**: Less reactive rebuilding, more proactive management
5. **Maintainability**: Clear separation of concerns by card type

## Migration Strategy

1. **Keep Current System**: As fallback during implementation
2. **Feature Flag**: Toggle between old/new queue systems
3. **A/B Testing**: Compare both approaches side-by-side
4. **Gradual Rollout**: Phase-by-phase implementation with testing

This plan ensures we benefit from Anki's decades of optimization while maintaining our current functionality during the transition.