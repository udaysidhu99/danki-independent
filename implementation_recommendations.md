# Implementation Recommendations for Danki Scheduler

## Overview

Based on comprehensive analysis of Anki's scheduler system, this document provides specific recommendations for implementing a compatible spaced repetition system in Danki that can match Anki's proven effectiveness while maintaining the project's goals of simplicity and performance.

## Phase-Based Implementation Strategy

### Phase 1: Foundation (M1 - Current Priority)
**Goal**: Implement robust SM-2 scheduler matching Anki's behavior

**Timeline**: Current development cycle

**Core Components**:
```python
# danki/engine/scheduler.py - Core SM-2 Implementation
class SM2Scheduler:
    def __init__(self, config: SchedulerConfig):
        self.config = config
        
    def schedule_card(self, card: Card, rating: Rating) -> CardUpdate:
        """Main scheduling method - matches Anki SM-2 behavior"""
        pass
        
    def build_session(self, deck_id: int, limits: DailyLimits) -> ReviewSession:
        """Build review session with proper card ordering"""
        pass

# Database schema updates needed
class Card:
    # Current schema is good, may need minor additions
    interval: int           # Days
    ease_factor: int        # * 1000 (e.g., 2500 = 250%)
    card_type: CardType     # NEW, LEARNING, REVIEW, RELEARNING
    queue: CardQueue        # Queue state
    due: int               # Days since epoch or position
    step_index: int        # Current learning step (if learning)
    lapses: int            # Number of lapses
```

**Key Features to Implement**:
1. **Learning Steps Progression**
   - Default steps: [10 minutes, 1 day]  
   - Configurable per deck
   - Proper Again/Hard/Good/Easy handling

2. **Review Interval Calculation**
   - Ease factor management (2.5 start, 1.3 minimum)
   - Late review handling with partial credit
   - Interval fuzzing (±5% randomization)

3. **Queue Management**
   - Learning cards have priority
   - New/review cards by due date
   - Proper sibling burying

**Implementation Priority**:
```python
# 1. Core state transitions (CRITICAL)
def transition_card_state(current_state: CardState, rating: Rating) -> CardState:
    """Handles all state transitions matching Anki behavior"""
    
# 2. Interval calculations (CRITICAL) 
def calculate_sm2_interval(card: Card, rating: Rating, days_late: int) -> int:
    """SM-2 interval calculation with Anki modifications"""
    
# 3. Queue building (HIGH)
def build_review_queue(deck_id: int, limits: DailyLimits) -> List[Card]:
    """Builds properly ordered review session"""
    
# 4. Learning step management (HIGH)
def advance_learning_step(card: Card, rating: Rating) -> CardState:
    """Manages progression through learning steps"""
```

### Phase 2: FSRS Integration (M2-M3)
**Goal**: Add FSRS as optional advanced scheduling algorithm

**Timeline**: After M1 completion, likely M2-M3 timeframe

**Core Components**:
```python
# danki/engine/fsrs.py - FSRS Implementation
class FSRSScheduler:
    def __init__(self, params: FSRSParams):
        self.params = params  # 19 parameters for v6
        
    def calculate_memory_state(
        self, 
        previous_state: Optional[MemoryState],
        rating: Rating
    ) -> MemoryState:
        """DSR model calculations"""
        pass
        
    def optimize_parameters(
        self, 
        review_history: List[ReviewLog]
    ) -> FSRSParams:
        """Machine learning parameter optimization"""
        pass

class MemoryState:
    difficulty: float   # 1.0 - 10.0
    stability: float    # Days for 90% retention
```

**Research and Development Tasks**:
1. Study FSRS implementation in detail
2. Implement parameter optimization (possibly via external library)
3. Create migration system from SM-2 to FSRS
4. Performance testing with large datasets

### Phase 3: Advanced Features (Post-MVP)
**Timeline**: Future enhancement cycles

**Features**:
- Filtered decks and custom study sessions
- Advanced statistics and forecasting  
- Automatic parameter optimization
- A/B testing framework for algorithm comparison

## Database Schema Recommendations

### Current Schema Assessment
The existing Danki schema is well-designed and compatible:

```python
# danki/engine/db.py - Current schema works well
# Minor additions needed:

class Card:
    # Add these fields for full compatibility:
    lapses: int = 0          # Track review→relearning transitions
    step_index: int = 0      # Current learning step (0-based)
    original_due: int = 0    # For filtered deck support
    original_deck_id: int = 0 # For filtered deck support
    
    # Optional FSRS fields (can be in metadata JSON initially):
    # stability: float = None
    # difficulty: float = None
```

### Review Log Enhancement
```sql
-- Add review logging table (critical for FSRS)
CREATE TABLE review_log (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    rating INTEGER NOT NULL,      -- 1-4 (Again-Easy)
    interval_before INTEGER NOT NULL,
    interval_after INTEGER NOT NULL,
    ease_factor INTEGER NOT NULL, -- * 1000
    review_time_ms INTEGER NOT NULL,
    card_type INTEGER NOT NULL,   -- 0=new, 1=learning, 2=review, 3=relearning
    
    FOREIGN KEY (card_id) REFERENCES cards (id)
);

CREATE INDEX ix_review_log_card_id ON review_log (card_id);
CREATE INDEX ix_review_log_timestamp ON review_log (timestamp);
```

## Specific Algorithm Implementation

### SM-2 Implementation Details

#### Ease Factor Management
```python
STARTING_EASE = 2500  # 250% (stored as int * 1000)
MINIMUM_EASE = 1300   # 130%

def update_ease_factor(current_ease: int, rating: Rating) -> int:
    """Update ease factor based on rating"""
    adjustments = {
        Rating.AGAIN: -200,  # -20 percentage points  
        Rating.HARD: -150,   # -15 percentage points
        Rating.GOOD: 0,      # No change
        Rating.EASY: 150,    # +15 percentage points
    }
    
    new_ease = current_ease + adjustments[rating]
    return max(new_ease, MINIMUM_EASE)
```

#### Interval Calculation
```python
def calculate_review_interval(
    card: Card, 
    rating: Rating, 
    days_late: int = 0
) -> int:
    """Calculate new interval for review cards"""
    current_interval = card.interval
    ease_factor = card.ease_factor / 1000.0
    
    if rating == Rating.AGAIN:
        # Lapse - return to relearning
        return int(current_interval * 0.5)  # Lapse multiplier
        
    elif rating == Rating.HARD:
        return max(1, int(current_interval * 1.2))  # Hard multiplier
        
    elif rating == Rating.GOOD:
        return max(1, int((current_interval + days_late/2) * ease_factor))
        
    elif rating == Rating.EASY:
        return max(1, int((current_interval + days_late) * ease_factor * 1.3))
```

#### Learning Steps Implementation
```python
DEFAULT_LEARNING_STEPS = [10, 1440]  # 10 minutes, 1 day (in minutes)

def advance_learning_card(card: Card, rating: Rating, steps: List[int]) -> CardUpdate:
    """Handle learning card progression"""
    if rating == Rating.AGAIN:
        # Reset to first step
        return CardUpdate(
            card_type=CardType.LEARNING,
            due=now() + timedelta(minutes=steps[0]),
            step_index=0
        )
    
    elif rating == Rating.HARD:
        # Repeat current step (minimum 10 minutes)
        current_step = steps[card.step_index]
        repeat_time = max(current_step, 10)
        return CardUpdate(
            due=now() + timedelta(minutes=repeat_time),
            step_index=card.step_index  # No advancement
        )
    
    elif rating in [Rating.GOOD, Rating.EASY]:
        next_step_index = card.step_index + 1
        
        if next_step_index >= len(steps):
            # Graduate to review
            graduating_interval = 1 if rating == Rating.GOOD else 4
            return CardUpdate(
                card_type=CardType.REVIEW,
                interval=graduating_interval,
                ease_factor=STARTING_EASE,
                due=now() + timedelta(days=graduating_interval),
                step_index=0
            )
        else:
            # Advance to next step
            next_step_minutes = steps[next_step_index]
            return CardUpdate(
                due=now() + timedelta(minutes=next_step_minutes),
                step_index=next_step_index
            )
```

### Queue Building Implementation
```python
def build_review_session(deck_id: int, limits: DailyLimits) -> List[Card]:
    """Build ordered review session matching Anki behavior"""
    
    # 1. Get due learning cards (highest priority)
    learning_cards = db.get_learning_cards_due(deck_id)
    
    # 2. Get due review cards  
    review_cards = db.get_review_cards_due(deck_id, limits.reviews_per_day)
    
    # 3. Get new cards up to daily limit
    new_cards = db.get_new_cards(deck_id, limits.new_per_day)
    
    # 4. Combine with proper interleaving
    session_cards = []
    
    # Learning cards first (all due learning)
    session_cards.extend(learning_cards)
    
    # Interleave new and review based on preferences
    # Default: show new cards before reviews
    if deck_preferences.new_before_review:
        session_cards.extend(new_cards)
        session_cards.extend(review_cards)
    else:
        # Mix new and review cards
        session_cards.extend(interleave_cards(new_cards, review_cards))
    
    return session_cards

def interleave_cards(new_cards: List[Card], review_cards: List[Card]) -> List[Card]:
    """Interleave new and review cards based on Anki's algorithm"""
    # Simplified version - more complex mixing in real Anki
    result = []
    new_iter = iter(new_cards)
    review_iter = iter(review_cards)
    
    try:
        while True:
            # Add one review card
            result.append(next(review_iter))
            # Add one new card  
            result.append(next(new_iter))
    except StopIteration:
        # Add remaining cards
        result.extend(new_iter)
        result.extend(review_iter)
    
    return result
```

## Integration with Existing Danki Code

### Scheduler Interface
```python
# danki/engine/scheduler.py - Main interface
class SpacedRepetitionScheduler:
    def __init__(self, algorithm: str = "sm2"):
        if algorithm == "sm2":
            self.impl = SM2Scheduler()
        elif algorithm == "fsrs":
            self.impl = FSRSScheduler() 
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    def schedule_card(self, card: Card, rating: Rating) -> CardUpdate:
        return self.impl.schedule_card(card, rating)
    
    def build_session(self, deck_id: int) -> ReviewSession:
        return self.impl.build_session(deck_id)
```

### UI Integration Points
```python
# danki/ui/screens/review.py - Review screen integration
class ReviewScreen:
    def handle_rating(self, rating: Rating):
        # Get current card state  
        card_update = self.scheduler.schedule_card(self.current_card, rating)
        
        # Update database
        self.db.update_card(self.current_card.id, card_update)
        
        # Log the review
        self.db.add_review_log(ReviewLog(
            card_id=self.current_card.id,
            rating=rating,
            interval_before=self.current_card.interval,
            interval_after=card_update.interval,
            review_time_ms=self.review_timer.elapsed()
        ))
        
        # Move to next card
        self.load_next_card()
```

## Performance Optimization Strategies

### Database Queries
```sql
-- Critical indexes for performance
CREATE INDEX ix_cards_deck_queue_due ON cards (deck_id, queue, due);
CREATE INDEX ix_cards_deck_type_due ON cards (deck_id, card_type, due);
CREATE INDEX ix_cards_due_id ON cards (due, id);  -- For consistent ordering

-- Query optimization
-- Use prepared statements for frequent queries
-- Batch database updates when possible
-- Consider WAL mode for SQLite
```

### Memory Management
```python
# Keep review sessions in memory but limit size
MAX_SESSION_SIZE = 1000  # Cards

class ReviewSession:
    def __init__(self, cards: List[Card]):
        # Only keep essential data in memory
        self.cards = [CardForReview(c) for c in cards[:MAX_SESSION_SIZE]]
        self.current_index = 0
        
class CardForReview:
    """Lightweight card representation for reviews"""
    def __init__(self, card: Card):
        self.id = card.id
        self.front = card.note.front
        self.back = card.note.back
        self.state = card.current_state()
```

## Testing Strategy

### Unit Tests (Critical)
```python
# Test SM-2 algorithm correctness
def test_ease_factor_updates():
    """Test ease factor changes match Anki exactly"""
    
def test_interval_calculations():
    """Test interval calculations for all rating types"""
    
def test_learning_progression():
    """Test learning step advancement"""
    
def test_graduation_logic():
    """Test learning → review transitions"""
    
def test_lapse_handling():
    """Test review → relearning transitions"""

# Integration tests
def test_full_review_session():
    """Test complete review session workflow"""
    
def test_queue_building():
    """Test proper card ordering and limits"""
```

### Compatibility Tests
```python
def test_anki_compatibility():
    """Import Anki deck and verify identical scheduling"""
    # Load Anki deck via JSONL
    # Run same review sequence in both systems
    # Compare resulting card states and intervals
```

## Migration and Compatibility

### Anki Import Compatibility
```python
# Ensure JSONL import preserves scheduling data
def import_anki_card(anki_data: dict) -> Card:
    """Convert Anki JSONL to Danki card with scheduling intact"""
    return Card(
        front=anki_data["front"],
        back=anki_data["back"],
        # Preserve any existing scheduling data
        interval=anki_data.get("interval", 0),
        ease_factor=anki_data.get("factor", 2500),
        due=convert_anki_due_date(anki_data.get("due", 0)),
        card_type=CardType.NEW  # Will be updated on first review
    )
```

### Configuration Migration  
```python
# Support Anki deck options format
class DeckOptions:
    def from_anki_format(self, anki_options: dict):
        """Convert Anki deck options to Danki format"""
        self.new_per_day = anki_options.get("newPerDay", 20)
        self.reviews_per_day = anki_options.get("revPerDay", 200)
        self.learning_steps = anki_options.get("delays", [1, 10])
        # ... other options
```

## Risk Mitigation

### Algorithm Correctness
- **Risk**: Subtle differences from Anki behavior
- **Mitigation**: Extensive compatibility testing with real Anki decks
- **Validation**: Side-by-side comparison with Anki for identical inputs

### Performance Issues
- **Risk**: Slow performance with large collections
- **Mitigation**: Proper database indexing, query optimization
- **Validation**: Test with collections of 10k+ cards

### Data Integrity  
- **Risk**: Loss of review history or progress
- **Mitigation**: Database transactions, backup/restore system
- **Validation**: Comprehensive error handling and recovery testing

## Success Metrics

### Functional Compatibility
- [ ] Pass 100% of Anki scheduling behavior tests
- [ ] Import Anki decks without losing scheduling data  
- [ ] Identical interval calculations for all rating combinations
- [ ] Proper learning step progression and graduation

### Performance Targets
- [ ] Review session building < 100ms for 10k card collections
- [ ] Card answer processing < 10ms per card
- [ ] Database queries optimized with proper indexing
- [ ] Memory usage < 100MB for active review sessions

### User Experience
- [ ] Seamless migration from Anki workflows
- [ ] Predictable interval behavior users can understand
- [ ] No loss of learning progress during algorithm changes
- [ ] Clear feedback on scheduling decisions

This implementation plan provides a clear path to achieve Anki-compatible scheduling in Danki while maintaining the project's goals of simplicity and performance. The phased approach ensures a solid foundation with SM-2 before adding advanced FSRS features.