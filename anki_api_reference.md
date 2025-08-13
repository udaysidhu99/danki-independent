# Anki API Reference: Key Methods, Data Structures, and Interfaces

## Overview

This document provides a comprehensive reference for the key APIs, data structures, and interfaces in the Anki scheduler system, extracted from the ankitects/anki repository analysis.

## Core Data Structures

### Card Representation

#### Card Database Schema
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    nid INTEGER NOT NULL,     -- Note ID (parent note)
    did INTEGER NOT NULL,     -- Deck ID
    ord INTEGER NOT NULL,     -- Card template ordinal  
    mod INTEGER NOT NULL,     -- Last modified timestamp
    usn INTEGER NOT NULL,     -- Update sequence number
    type INTEGER NOT NULL,    -- Card type (0=new, 1=learning, 2=review, 3=relearning)
    queue INTEGER NOT NULL,   -- Queue state (-3=user buried, -2=sched buried, -1=suspended, 0=new, 1=learning, 2=review, 3=in learning)
    due INTEGER NOT NULL,     -- Due date (days since epoch) or position for new cards
    ivl INTEGER NOT NULL,     -- Current interval in days
    factor INTEGER NOT NULL,  -- Ease factor * 1000 (e.g., 2500 = 250%)
    reps INTEGER NOT NULL,    -- Total number of reviews
    lapses INTEGER NOT NULL,  -- Number of lapses (review→relearning transitions)
    left INTEGER NOT NULL,    -- Learning: steps remaining | Review: unused
    odue INTEGER NOT NULL,    -- Original due (for filtered decks)
    odid INTEGER NOT NULL,    -- Original deck ID (for filtered decks)  
    flags INTEGER NOT NULL,   -- User flags (unused in scheduling)
    data TEXT NOT NULL        -- JSON extra data
);
```

#### Rust Card Structure
```rust
pub struct Card {
    pub id: CardId,
    pub note_id: NoteId,
    pub deck_id: DeckId,
    pub template_idx: u16,
    pub mtime: TimestampSecs,
    pub usn: Usn,
    pub ctype: CardType,
    pub queue: CardQueue,
    pub due: i32,
    pub interval: u32,
    pub ease_factor: u16,  // * 1000
    pub reps: u32,
    pub lapses: u32,
    pub remaining_steps: u32,
    pub original_due: i32,
    pub original_deck_id: DeckId,
    pub flags: u8,
    pub data: String,  // JSON
}
```

### Card States

#### State Enumeration
```rust
pub enum CardState {
    Normal(NormalState),
    Filtered(FilteredState),
}

pub enum NormalState {
    New(NewState),
    Learning(LearnState), 
    Review(ReviewState),
    Relearning(RelearnState),
}

pub enum FilteredState {
    Preview(PreviewState),
    Rescheduling(ReschedulingState),
}
```

#### Learning State Details
```rust
pub struct LearnState {
    pub remaining_steps: NonZeroU32,
    pub scheduled_secs: u32,
    pub elapsed_secs: u32,
    pub memory_state: Option<MemoryState>,  // For FSRS
}
```

#### Review State Details  
```rust
pub struct ReviewState {
    pub scheduled_days: u32,
    pub elapsed_days: u32,
    pub ease_factor: f32,
    pub lapses: u32,
    pub memory_state: Option<MemoryState>,  // For FSRS
}
```

### Rating System

#### Answer Ratings
```rust
pub enum Rating {
    Again = 1,  // Failed recall - reset/lapse
    Hard = 2,   // Difficult recall - reduced interval
    Good = 3,   // Normal recall - standard interval
    Easy = 4,   // Effortless recall - bonus interval
}
```

#### Rating Constraints
```rust
impl Rating {
    pub fn as_number(self) -> u8 { self as u8 }
    
    pub fn from_number(num: u8) -> Option<Rating> {
        match num {
            1 => Some(Rating::Again),
            2 => Some(Rating::Hard), 
            3 => Some(Rating::Good),
            4 => Some(Rating::Easy),
            _ => None,
        }
    }
}
```

## Core Scheduler Interfaces

### Main Scheduler API

#### Scheduler Information
```rust
pub struct SchedulerInfo {
    pub version: SchedulerVersion,
    pub timing: SchedTimingToday,
}

pub enum SchedulerVersion {
    V1, // Legacy
    V2, // Current SM-2
    V3, // FSRS (future)
}

impl Collection {
    pub fn scheduler_info(&mut self) -> Result<SchedulerInfo> {
        let timing = self.timing_today()?;
        Ok(SchedulerInfo {
            version: self.scheduler_version(),
            timing,
        })
    }
}
```

#### Daily Timing Management
```rust
pub struct SchedTimingToday {
    pub days_elapsed: u32,        // Days since collection creation
    pub next_day_at: TimestampSecs, // When next day begins (rollover)
    pub now: TimestampSecs,       // Current timestamp
}

impl Collection {
    pub fn timing_today(&mut self) -> Result<SchedTimingToday> {
        self.timing_for_timestamp(TimestampSecs::now())
    }
    
    pub fn timing_for_timestamp(&mut self, now: TimestampSecs) -> Result<SchedTimingToday> {
        let created_days = (self.storage.creation_timestamp().0 / 86400) as u32;
        let rollover_hour = self.get_config_default("rollover", 4i64) as i8;
        
        sched_timing_today_v2_new(
            created_days,
            now,
            rollover_hour,
            self.get_local_mins_west(),
        )
    }
}
```

### Queue Management API

#### Queue Structure
```rust
pub struct CardQueues {
    pub main: VecDeque<QueueEntry>,
    pub intraday_learning: VecDeque<QueueEntry>,
    pub current_day: u32,
    pub current_learning_cutoff: TimestampSecs,
}

pub struct QueueEntry {
    pub card: Card,
    pub next_states: NextCardStates,
}
```

#### Queue Operations
```rust
impl CardQueues {
    pub fn iter(&self) -> impl Iterator<Item = &QueueEntry> {
        // Priority order: learning now, main queue, learning future
        self.intraday_learning
            .iter()
            .filter(|entry| entry.due_now())
            .chain(self.main.iter())
            .chain(
                self.intraday_learning
                    .iter()
                    .filter(|entry| !entry.due_now())
            )
    }
    
    pub fn get_queued_cards(
        &self, 
        limit: usize, 
        intraday_learning_only: bool
    ) -> Vec<QueuedCard> {
        let iter = if intraday_learning_only {
            self.intraday_learning.iter()
        } else {
            self.iter()
        };
        
        iter.take(limit)
            .map(|entry| QueuedCard::from(entry))
            .collect()
    }
}
```

### Card Answer Processing

#### Answer Processing API
```rust
pub struct CardAnswer {
    pub card_id: CardId,
    pub current_state: CardState,
    pub new_state: CardState,
    pub rating: Rating,
    pub answered_at: TimestampSecs,
    pub milliseconds_taken: u32,
}

impl Collection {
    pub fn answer_card(&mut self, input: &CardAnswer) -> Result<()> {
        // Update card state
        let mut card = self.storage.get_card(input.card_id)?;
        card.apply_state(&input.new_state);
        
        // Log the review
        self.add_review_log(ReviewLog {
            id: ReviewLogId(0),
            cid: input.card_id,
            usn: self.usn(),
            button_chosen: input.rating as u8,
            interval: card.interval as i32,
            last_interval: input.current_state.interval() as i32,
            ease_factor: card.ease_factor,
            time_taken: input.milliseconds_taken,
            review_kind: input.new_state.revlog_kind(),
        })?;
        
        // Update card in database
        self.storage.update_card(&card)?;
        
        // Update queue state  
        self.clear_study_queues();
        
        Ok(())
    }
}
```

#### State Transition API
```rust
pub trait StateContext {
    fn learning_steps(&self) -> &[u32];
    fn graduating_interval_good(&self) -> u32;
    fn graduating_interval_easy(&self) -> u32;
    fn hard_multiplier(&self) -> f32;
    fn easy_multiplier(&self) -> f32;
    fn lapse_multiplier(&self) -> f32;
    fn relearning_steps(&self) -> &[u32];
    fn fsrs_memory_state(&self) -> Option<&MemoryState>;
}

pub struct NextCardStates {
    pub again: CardState,
    pub hard: CardState,
    pub good: CardState,
    pub easy: CardState,
}

impl CardState {
    pub fn next_states(&self, ctx: &StateContext) -> NextCardStates {
        match self {
            CardState::Normal(state) => state.next_states(ctx),
            CardState::Filtered(state) => state.next_states(ctx),
        }
    }
}
```

## SM-2 Algorithm Implementation

### Ease Factor Management
```rust
const STARTING_EASE_FACTOR: f32 = 2.5;
const MINIMUM_EASE_FACTOR: f32 = 1.3;

impl ReviewState {
    pub fn answer_ease_factor(&self, rating: Rating) -> f32 {
        let current_ease = self.ease_factor;
        let adjustment = match rating {
            Rating::Again => -0.2,
            Rating::Hard => -0.15,
            Rating::Good => 0.0,
            Rating::Easy => 0.15,
        };
        (current_ease + adjustment).max(MINIMUM_EASE_FACTOR)
    }
}
```

### Interval Calculation
```rust
impl ReviewState {
    pub fn interval_good(&self, ctx: &StateContext) -> u32 {
        let current_interval = self.scheduled_days as f32;
        let days_late = self.elapsed_days.saturating_sub(self.scheduled_days) as f32;
        
        ((current_interval + days_late / 2.0) * self.ease_factor) as u32
    }
    
    pub fn interval_hard(&self, ctx: &StateContext) -> u32 {
        (self.scheduled_days as f32 * ctx.hard_multiplier()) as u32
    }
    
    pub fn interval_easy(&self, ctx: &StateContext) -> u32 {
        let current_interval = self.scheduled_days as f32;
        let days_late = self.elapsed_days.saturating_sub(self.scheduled_days) as f32;
        
        ((current_interval + days_late) * self.ease_factor * ctx.easy_multiplier()) as u32
    }
}
```

### Learning Steps Management
```rust
impl LearnState {
    pub fn answer_good(&self, ctx: &StateContext) -> CardState {
        if self.remaining_steps.get() == 1 {
            // Graduate to review
            let interval = ctx.graduating_interval_good();
            CardState::Normal(NormalState::Review(ReviewState {
                scheduled_days: interval,
                elapsed_days: 0,
                ease_factor: STARTING_EASE_FACTOR,
                lapses: 0,
                memory_state: None,
            }))
        } else {
            // Advance to next learning step
            let steps = ctx.learning_steps();
            let current_step_index = steps.len() - self.remaining_steps.get() as usize;
            let next_step_secs = steps[current_step_index + 1] * 60;
            
            CardState::Normal(NormalState::Learning(LearnState {
                remaining_steps: NonZeroU32::new(self.remaining_steps.get() - 1)
                    .unwrap(),
                scheduled_secs: next_step_secs,
                elapsed_secs: 0,
                memory_state: None,
            }))
        }
    }
}
```

## FSRS Algorithm Implementation  

### Memory State Structure
```rust
pub struct MemoryState {
    pub stability: f32,    // Days for recall probability to drop from 100% to 90%
    pub difficulty: f32,   // Inherent complexity (1.0 - 10.0)
}

pub struct FsrsParams {
    pub params: Vec<f32>,  // 19 parameters for FSRS v6
}
```

### Core FSRS Calculations
```rust
pub fn fsrs_memory_state(
    previous_state: Option<MemoryState>,
    grade: Rating,
    params: &FsrsParams,
) -> MemoryState {
    let difficulty = if let Some(prev) = previous_state {
        update_difficulty(prev.difficulty, grade, params)
    } else {
        initial_difficulty(grade, params)
    };
    
    let stability = if let Some(prev) = previous_state {
        update_stability(prev.stability, difficulty, grade, params)
    } else {
        initial_stability(grade, params)
    };
    
    MemoryState { stability, difficulty }
}

pub fn fsrs_interval(
    stability: f32,
    target_retention: f32,
) -> u32 {
    (stability * (target_retention / 0.9).ln() / 0.9_f32.ln()) as u32
}
```

### Retrievability Calculation
```rust
const DECAY: f32 = -0.5;

pub fn retrievability(elapsed_days: f32, stability: f32) -> f32 {
    let factor = DECAY * elapsed_days / stability;
    (1.0 + factor.exp()).powf(DECAY)
}
```

## Database Query Interface

### Card Selection Queries
```rust
impl Collection {
    pub fn due_cards(&mut self, deck_id: DeckId, limit: u32) -> Result<Vec<Card>> {
        self.storage.db.prepare_cached(
            "SELECT * FROM cards 
             WHERE did = ? AND queue IN (1, 2, 3) AND due <= ?
             ORDER BY due, id LIMIT ?"
        )?.query_and_then(
            params![deck_id, self.timing_today()?.days_elapsed, limit],
            |row| Card::from_row(row)
        )?.collect()
    }
    
    pub fn new_cards(&mut self, deck_id: DeckId, limit: u32) -> Result<Vec<Card>> {
        self.storage.db.prepare_cached(
            "SELECT * FROM cards 
             WHERE did = ? AND queue = 0 
             ORDER BY due, id LIMIT ?"
        )?.query_and_then(
            params![deck_id, limit],
            |row| Card::from_row(row)
        )?.collect()
    }
}
```

### Review Log Interface
```rust
pub struct ReviewLog {
    pub id: ReviewLogId,
    pub cid: CardId,
    pub usn: Usn,
    pub button_chosen: u8,     // 1-4 (Again-Easy)
    pub interval: i32,         // New interval after review
    pub last_interval: i32,    // Previous interval
    pub ease_factor: u16,      // * 1000
    pub time_taken: u32,       // Milliseconds
    pub review_kind: u8,       // 0=learn, 1=review, 2=relearn, 3=early
}

impl Collection {
    pub fn add_review_log(&mut self, log: ReviewLog) -> Result<()> {
        self.storage.db.prepare_cached(
            "INSERT INTO revlog 
             (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )?.execute(params![
            log.id,
            log.cid,
            log.usn,
            log.button_chosen,
            log.interval,
            log.last_interval,
            log.ease_factor,
            log.time_taken,
            log.review_kind,
        ])?;
        Ok(())
    }
}
```

## Configuration Management

### Deck Options Schema
```rust
pub struct DeckOptions {
    pub new_per_day: u32,           // Daily new card limit
    pub rev_per_day: u32,           // Daily review limit  
    pub learning_steps: Vec<u32>,   // Learning steps in minutes
    pub graduating_ivl: u32,        // Graduating interval
    pub easy_ivl: u32,              // Easy interval from learning
    pub starting_ease: f32,         // Starting ease factor
    pub easy_bonus: f32,            // Easy button multiplier
    pub hard_factor: f32,           // Hard button multiplier
    pub lapse_mult: f32,            // Lapse interval multiplier
    pub min_ivl: u32,               // Minimum interval
    pub max_ivl: u32,               // Maximum interval
    pub relearning_steps: Vec<u32>, // Relearning steps
    pub leech_threshold: u32,       // Leech detection threshold
    pub leech_action: LeechAction,  // What to do with leeches
}
```

### FSRS Configuration
```rust
pub struct FsrsConfig {
    pub enabled: bool,
    pub target_retention: f32,      // Desired retention rate (0.7-0.97)
    pub params: Option<FsrsParams>, // Optimized parameters
    pub auto_optimize: bool,        // Enable parameter optimization
    pub min_reviews: u32,           // Minimum reviews before optimization
}
```

## Error Handling

### Common Error Types
```rust
pub enum SchedulerError {
    InvalidCardState,
    InvalidRating,
    DatabaseError(rusqlite::Error),
    InvalidConfiguration,
    OptimizationFailed,
}

impl From<rusqlite::Error> for SchedulerError {
    fn from(err: rusqlite::Error) -> Self {
        SchedulerError::DatabaseError(err)
    }
}
```

## Performance Considerations

### Database Indexes
```sql
-- Essential indexes for scheduler performance
CREATE INDEX ix_cards_did_queue_due ON cards (did, queue, due);
CREATE INDEX ix_cards_nid ON cards (nid);
CREATE INDEX ix_revlog_cid ON revlog (cid);
CREATE INDEX ix_revlog_usn ON revlog (usn);
```

### Memory Management
```rust
// Queue management with memory limits
const MAX_QUEUE_SIZE: usize = 1000;

impl CardQueues {
    pub fn is_at_capacity(&self) -> bool {
        self.main.len() + self.intraday_learning.len() >= MAX_QUEUE_SIZE
    }
}
```

This API reference provides the essential interfaces needed to implement a compatible Anki scheduler system, covering both SM-2 and FSRS algorithms with full database integration and performance considerations.