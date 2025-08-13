# Anki Algorithm Comparison: SM-2 vs FSRS

## Executive Summary

This document provides a detailed comparison between Anki's SM-2 implementation and the Free Spaced Repetition Scheduler (FSRS) algorithm, analyzing their mathematical foundations, practical performance, and implementation trade-offs.

## Algorithm Overview

### SM-2 (SuperMemo 2)
- **Origins**: Developed by Piotr Wozniak for SuperMemo in 1987
- **Core Concept**: Ease factor-based interval multiplication
- **Anki Modifications**: 4-button rating system, lapse handling, interval fuzzing
- **Target**: Simple, predictable spaced repetition

### FSRS (Free Spaced Repetition Scheduler)
- **Origins**: Modern algorithm based on DSR memory model (2023+)
- **Core Concept**: Memory state prediction using difficulty, stability, retrievability
- **Optimization**: Machine learning parameter fitting
- **Target**: Optimal retention with minimal reviews

## Mathematical Foundations

### SM-2 Core Formulas

#### Ease Factor Calculation
```
Initial Ease Factor: 2.5
Minimum Ease Factor: 1.3

Ease Adjustments:
- Again: EF - 0.2
- Hard: EF - 0.15  
- Good: EF (no change)
- Easy: EF + 0.15
```

#### Interval Calculation (Review Cards)
```
Good Answer:
new_interval = (current_interval + days_late/2) * ease_factor

Hard Answer:
new_interval = current_interval * hard_multiplier  // ~1.2

Easy Answer:
new_interval = (current_interval + days_late) * ease_factor * easy_multiplier  // ~1.3

Again Answer:
- Transition to relearning state
- Apply lapse multiplier (~0.5)
- Reset to relearning steps
```

#### Learning Steps Progression
```
Default Steps: [1 min, 10 min]
Graduating Interval: 1 day
Easy Interval: 4 days

Progression:
- Again: Reset to first step
- Hard: Repeat current step (minimum 10 minutes)
- Good: Advance to next step
- Easy: Graduate immediately (if enabled)
```

### FSRS Core Formulas

#### DSR Model Components
```
D = Difficulty (1.0 - 10.0): Inherent complexity of material
S = Stability (days): Time for retrievability to drop from 100% to 90%
R = Retrievability (0.0 - 1.0): Probability of successful recall
```

#### Retrievability Calculation
```
R(t,S) = (1 + DECAY * t/S)^(-1/DECAY)

Where:
- t = elapsed time since last review (days)
- S = current stability 
- DECAY = constant ensuring R(S,S) = 0.9
```

#### Stability After Review (FSRS v6)
```
S' = S * e^(w[17] * (G - 3 + w[18])) * S^(-w[19])

Where:
- S = current stability
- G = grade (1=Again, 2=Hard, 3=Good, 4=Easy)
- w[17], w[18], w[19] = learned parameters
```

#### Difficulty Evolution
```
D' = D + w[6] * (G - 3)
D' = constrain(D', 1.0, 10.0)

With mean reversion to prevent "difficulty hell"
```

#### Interval Calculation
```
For target retention R_target (typically 0.9):
interval = S * ln(R_target / 0.9) / ln(0.9)
```

## Parameter Systems Comparison

### SM-2 Parameters (Per Deck)
```
Learning Steps: [1, 10] minutes (configurable)
Graduating Interval: 1 day
Easy Interval: 4 days
Starting Ease: 250%
Easy Bonus: 130%
Hard Interval: 120%
Lapse Multiplier: 50%
Minimum Interval: 1 day
Maximum Interval: 36500 days
```

### FSRS Parameters
```
Total Parameters: 19 floating-point values (v6)
Default Training: 20,000+ users, 700M+ reviews
Optimization Target: Minimize log-loss on review predictions

Key Parameter Groups:
- w[0-3]: Initial stability based on first review grade
- w[4]: Difficulty decay rate  
- w[5-8]: Stability increase factors by grade
- w[9-15]: Advanced stability calculations
- w[16-18]: Grade-dependent stability modifications
```

## Performance Comparison

### Efficiency Metrics

#### Review Load Reduction
- **FSRS**: 20-30% fewer reviews for same retention
- **SM-2**: Baseline performance, well-established
- **Measurement**: Reviews per retained item over time

#### Retention Accuracy
- **FSRS**: ~85% prediction accuracy for individual reviews
- **SM-2**: ~75% prediction accuracy (estimated)
- **Target**: Both aim for ~90% retention at review time

### Handling Edge Cases

#### Late Reviews
```
SM-2: 
- Partial credit for lateness: (interval + days_late/2) * ease
- Can lead to interval explosion with long delays

FSRS:
- Accounts for memory decay during delay
- Automatically adjusts next interval based on current retrievability
- More robust to irregular review schedules
```

#### Initial Learning
```
SM-2:
- Fixed learning steps regardless of material difficulty
- All cards follow same progression pattern
- Simple, predictable behavior

FSRS:
- Adapts initial intervals based on estimated difficulty
- Faster progression for easy material
- More reviews for difficult material initially
```

#### Long-term Retention
```
SM-2:
- Ease factor can get "stuck" at minimum (130%)
- "Ease hell" problem for difficult cards
- Linear interval growth pattern

FSRS:
- Difficulty includes mean reversion
- Prevents permanent labeling of cards as "hard"
- Exponential stability growth with successful reviews
```

## Implementation Complexity

### SM-2 Implementation
```rust
// Simplified SM-2 interval calculation
fn calculate_sm2_interval(
    current_interval: u32,
    ease_factor: f32,
    grade: Rating,
    days_late: u32
) -> u32 {
    match grade {
        Rating::Again => 1, // Reset to learning
        Rating::Hard => (current_interval as f32 * 1.2) as u32,
        Rating::Good => ((current_interval + days_late/2) as f32 * ease_factor) as u32,
        Rating::Easy => ((current_interval + days_late) as f32 * ease_factor * 1.3) as u32,
    }
}

// Simple ease factor update
fn update_ease_factor(current_ease: f32, grade: Rating) -> f32 {
    let adjustment = match grade {
        Rating::Again => -0.2,
        Rating::Hard => -0.15,
        Rating::Good => 0.0,
        Rating::Easy => 0.15,
    };
    (current_ease + adjustment).max(1.3)
}
```

**Complexity**: ~100 lines of core logic

### FSRS Implementation
```rust
// FSRS requires significantly more complex calculations
fn calculate_fsrs_interval(
    stability: f32,
    difficulty: f32,
    grade: Rating,
    params: &[f32; 19],
    target_retention: f32
) -> (u32, f32, f32) {
    // Update difficulty with mean reversion
    let new_difficulty = update_difficulty(difficulty, grade, params);
    
    // Calculate new stability based on previous stability and grade
    let new_stability = calculate_stability(stability, difficulty, grade, params);
    
    // Compute interval for target retention
    let interval = stability_to_interval(new_stability, target_retention);
    
    (interval, new_stability, new_difficulty)
}
```

**Complexity**: ~500+ lines with parameter optimization

## Practical Trade-offs

### SM-2 Advantages
1. **Simplicity**: Easy to understand and debug
2. **Predictability**: Users can intuitively understand interval changes  
3. **Performance**: Minimal computational overhead
4. **Compatibility**: Decades of proven use across platforms
5. **Transparency**: Clear relationship between answers and intervals

### SM-2 Disadvantages
1. **Ease Hell**: Cards can get stuck at minimum ease
2. **Inflexibility**: Same learning pattern for all material types
3. **Late Review Handling**: Poor adaptation to irregular schedules
4. **Suboptimal Intervals**: Not personalized to individual memory patterns

### FSRS Advantages
1. **Personalization**: Adapts to individual memory patterns
2. **Efficiency**: 20-30% fewer reviews for same retention
3. **Robustness**: Better handling of irregular review schedules
4. **Scientific Foundation**: Based on modern memory research
5. **Continuous Improvement**: Parameters improve with more data

### FSRS Disadvantages
1. **Complexity**: Difficult to understand interval calculations
2. **Black Box**: Users cannot easily predict interval changes
3. **Computational Cost**: Requires parameter optimization
4. **Data Dependency**: Needs sufficient review history for optimization
5. **Stability**: Algorithm still evolving (v1 → v6)

## Migration Considerations

### From SM-2 to FSRS
```
Data Preservation:
✓ All review history maintained
✓ Card ease factors used to estimate initial difficulty
✓ Intervals preserved during transition
✓ No data loss during conversion

Behavioral Changes:
- Intervals may change significantly for some cards
- More consistent review load over time
- Better adaptation to user's actual memory performance
- Requires initial calibration period
```

### Hybrid Approach (Anki 23.10+)
```
Per-Deck Selection:
- Users can choose SM-2 or FSRS per deck
- Allows gradual migration and comparison
- Essential decks can stay on familiar SM-2
- Experimental decks can test FSRS

Implementation:
- Same card state system supports both algorithms
- Review logs compatible with both systems
- Statistics can compare performance across algorithms
```

## Performance Benchmarks

### Real-world Data (Open Spaced Repetition Project)
```
Dataset: 20,000+ users, 700M+ reviews

Retention Accuracy:
- FSRS: ~85% correct predictions
- SM-2: ~75% correct predictions  

Review Efficiency:
- FSRS: 20-30% fewer reviews for 90% retention
- SM-2: Baseline (100% relative efficiency)

Optimization Results:
- FSRS shows consistent improvement across user types
- Benefits increase with larger review history
- Most improvement in first 6 months of use
```

### Synthetic Benchmarks
```
Simulated Optimal Learner:
- Perfect memory strength tracking
- Optimal interval spacing
- FSRS approaches theoretical optimum

Simulated Irregular Learner:
- Variable review delays
- Inconsistent daily practice
- FSRS significantly outperforms SM-2
```

## Recommendations

### Use SM-2 When:
- **Learning System**: Educational tool where transparency matters
- **Minimal Data**: New users without review history
- **Simple Requirements**: Basic spaced repetition sufficient
- **Resource Constraints**: Minimal computational resources
- **Proven Stability**: Mission-critical applications requiring predictability

### Use FSRS When:
- **Personal Learning**: Individual users wanting optimized performance
- **Rich Data**: Sufficient review history for parameter optimization
- **Irregular Schedules**: Users with inconsistent review patterns
- **Efficiency Focus**: Minimizing total review time important
- **Modern Features**: Want cutting-edge spaced repetition technology

### Implementation Strategy for Danki
```
Phase 1: Implement robust SM-2
- Proven, stable foundation
- Easy to debug and validate
- Immediate compatibility with Anki expectations

Phase 2: Add FSRS as optional feature  
- Research implementation in Anki codebase
- Implement parameter optimization
- Provide user choice between algorithms

Phase 3: Advanced features
- Automatic algorithm recommendation
- A/B testing framework for personal optimization
- Hybrid scheduling based on card characteristics
```

## Conclusion

Both SM-2 and FSRS serve important roles in spaced repetition systems:

- **SM-2** provides a stable, understandable foundation suitable for most users
- **FSRS** offers significant efficiency improvements for users willing to embrace complexity

For Danki implementation, starting with a robust SM-2 system provides the best foundation, with FSRS as an advanced feature for optimization-focused users. This approach balances immediate utility with future enhancement potential while maintaining compatibility with user expectations from Anki.