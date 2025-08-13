# Anki Scheduler Analysis Project

This directory contains comprehensive analysis of Anki's open-source scheduling system to upgrade Danki's implementation with battle-tested algorithms.

## Overview

**Objective**: Analyze and document Anki's scheduling engine to implement proven spaced repetition algorithms in Danki.

**Target Repository**: https://github.com/ankitects/anki  
**Focus Areas**: Scheduler algorithms, card state management, session building, advanced features

## Analysis Documents

### Core Analysis (To be completed by specialized agent)
- [`anki_scheduler_analysis.md`](./anki_scheduler_analysis.md) - Complete system documentation
- [`anki_algorithm_comparison.md`](./anki_algorithm_comparison.md) - SM-2 vs FSRS detailed comparison  
- [`anki_api_reference.md`](./anki_api_reference.md) - Key methods and data structures
- [`implementation_recommendations.md`](./implementation_recommendations.md) - Migration strategy for Danki

### Implementation Planning
- [`enhanced_architecture.md`](./enhanced_architecture.md) - New scheduler architecture design
- [`migration_strategy.md`](./migration_strategy.md) - Step-by-step implementation plan
- [`testing_strategy.md`](./testing_strategy.md) - Validation and testing approach

## Repository Structure Analysis Target

```
ankitects/anki/
├── rslib/src/scheduler/          # Modern Rust scheduler (PRIMARY FOCUS)
├── pylib/anki/scheduler/         # Python scheduler interface
├── rslib/src/scheduler/states/   # Card state management
├── rslib/src/scheduler/timing/   # Review timing calculations
└── rslib/src/scheduler/fsrs/     # FSRS algorithm implementation
```

## Key Areas for Analysis

### 1. **Algorithm Implementations**
- **FSRS** - Modern Free Spaced Repetition Scheduler
- **SM-2+ Enhancements** - Anki's improvements over basic SM-2
- **Learning Steps** - New card introduction sequences
- **Relearning Logic** - Lapsed card handling

### 2. **Session Management**
- Daily limits and queue building
- Sibling card burying/handling
- Deck options and preferences
- Review session optimization

### 3. **Advanced Features**
- Filtered decks and custom study
- Timezone and day boundary handling
- Review history and statistics
- Performance optimizations

## Success Criteria

### Analysis Completeness
- [ ] Full documentation of Anki's scheduler architecture
- [ ] Detailed algorithm specifications (SM-2+, FSRS)
- [ ] API reference for key scheduling methods
- [ ] Clear implementation roadmap for Danki

### Implementation Readiness
- [ ] Backwards-compatible migration strategy
- [ ] Performance benchmarking approach
- [ ] Testing methodology defined
- [ ] Timeline and resource estimates

## Next Steps

1. **Deploy Specialized Analysis Agent** (Next session)
   - Deep dive into Anki's scheduler codebase
   - Generate comprehensive documentation
   - Identify key implementation patterns

2. **Implementation Planning** (Following sessions)
   - Design enhanced scheduler architecture
   - Plan gradual migration strategy
   - Set up testing and validation framework

3. **Development & Integration** (Future sessions)
   - Implement enhanced SM-2 algorithm
   - Add FSRS algorithm option
   - Build advanced analytics system

---

**Status**: 📋 Documentation structure prepared  
**Next**: Deploy specialized agent for Anki codebase analysis  
**Timeline**: Analysis phase 1-2 sessions, Implementation 3-4 sessions