# Anki Scheduler API Reference

**Status**: 📋 Template - To be completed by specialized analysis agent  
**Purpose**: Document key methods, data structures, and interfaces

---

## Core Scheduler Interface

### Main Scheduler Class
[Analyze: Primary scheduler class and initialization]

```rust
// Template - extract actual implementation
struct Scheduler {
    // Key properties to document
}

impl Scheduler {
    // Key methods to analyze and document
}
```

### Card State Management
[Document: How card states are represented and modified]

```rust  
// Template - card state definitions
enum CardState {
    // Document all possible states
}

struct CardData {
    // Key card properties for scheduling
}
```

## Algorithm Implementations

### SM-2+ Implementation
[Extract: Key methods for SM-2+ algorithm]

```rust
// Template - SM-2+ specific methods
impl Sm2Scheduler {
    fn calculate_interval() -> Duration
    fn update_ease_factor() -> f32
    fn handle_learning_step() -> CardState
    fn process_review_response() -> SchedulingUpdate
}
```

### FSRS Implementation  
[Extract: Key methods for FSRS algorithm]

```rust
// Template - FSRS specific methods
impl FsrsScheduler {
    fn calculate_stability() -> f32
    fn calculate_difficulty() -> f32
    fn predict_retention() -> f32
    fn optimize_parameters() -> FsrsParams
}
```

## Session Building API

### Queue Construction
[Document: How review sessions are built]

```rust
// Template - session building methods
impl SessionBuilder {
    fn build_review_queue() -> Vec<Card>
    fn apply_daily_limits() -> FilteredCards
    fn handle_sibling_burying() -> BuriedCards
    fn prioritize_cards() -> OrderedQueue
}
```

### Deck Options Integration
[Document: How per-deck settings affect scheduling]

## Database Interface

### Card Table Schema
[Extract: Exact database schema used by Anki]

```sql
-- Template - analyze actual schema
CREATE TABLE cards (
    -- Document all columns and their purposes
);

CREATE TABLE revlog (
    -- Document review log structure  
);
```

### Query Patterns
[Document: Key database queries used by scheduler]

## Configuration System

### Deck Preferences
[Document: How deck-specific options are structured]

```json
// Template - deck option structure
{
  "scheduler_version": "?",
  "learning_steps": [],
  "relearning_steps": [],
  "daily_limits": {},
  "algorithm_choice": "?"
}
```

### Global Settings
[Document: Application-wide scheduler settings]

## Performance Optimizations

### Caching Strategies
[Analyze: How Anki optimizes scheduling calculations]

### Batch Operations
[Document: Efficient handling of multiple cards]

### Index Usage  
[Analyze: Database indexing for scheduler queries]

## Integration Points

### UI Interfaces
[Document: How scheduler connects to user interface]

### Statistics Generation
[Analyze: How scheduling data feeds analytics]

### Import/Export
[Document: How scheduling data is preserved]

## Error Handling

### Invalid States
[Analyze: How Anki handles corrupted card data]

### Migration Logic
[Document: Upgrading from older scheduler versions]

## Python Interface (pylib)

### Python Wrapper Methods
[Document: How Python code interfaces with Rust scheduler]

```python
# Template - Python scheduler interface
class Scheduler:
    def build_review_queue(self) -> List[Card]:
        pass
        
    def answer_card(self, card: Card, response: Response) -> None:
        pass
```

---

**Analysis Priority**:
1. Core scheduling methods (interval calculation, state transitions)
2. Session building logic (queue construction, limits)
3. Database schema and query patterns
4. Configuration and options system
5. Performance optimization techniques

**Output**: Complete API reference for Danki implementation compatibility