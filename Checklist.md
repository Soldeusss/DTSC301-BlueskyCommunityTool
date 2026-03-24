## MVP Checklist for Bluesky Community Tool (Prioritized)

### Phase 1 — Foundation (Must Have)
- [X] Set up `.venv`, dependencies, and project config
- [X] Define minimal data schema (`feed`, `post`, `hashtag`, `engagement`)
- [X] Build ingestion pipeline for:
  - [X] Popular custom feeds
  - [X] Trending hashtags/topics
- [X] Store normalized records in local database/files (single source of truth)
- [X] Add basic logging + retry handling for ingestion failures

### Phase 2 — Core Intelligence (Must Have)
- [X] Implement hashtag/keyword extraction from ingested posts
- [X] Create simple topic grouping logic (rule-based or lightweight clustering)
- [X] Compute core popularity metrics:
  - [X] Subscriber count
  - [X] Post volume
  - [X] Like count (or available engagement proxy)
- [X] Define and implement a transparent feed ranking score

### Phase 3 — User-Facing Output (Must Have)
- [X] Build topic lookup tool (CLI or minimal API)
- [X] Return top recommended feeds for an input topic
- [X] Include short explanation for each recommendation (why it matched)

### Phase 4 — Visual Deliverables (Should Have)
- [X] Generate one word cloud per top feed/topic
- [X] Build feed relation graph for an input topic:
  - [X] Show top feeds
  - [X] Show related secondary feeds
- [X] Export visuals as interactive HTML

### Phase 5 — Validation & Demo Readiness (Must Have)
- [ ] Add basic unit tests for parsing, scoring, and ranking
- [ ] Run end-to-end test: ingestion → mapping → ranking → output
- [ ] Validate output quality on 3–5 sample topics
- [ ] Prepare demo script and sample outputs for presentation

## MVP Definition of Done
- [ ] User can input a topic and receive ranked feed recommendations
- [ ] Recommendations are based on both relevance and popularity statistics
- [ ] Tool outputs at least:
  - [ ] One word cloud
  - [ ] One feedmap relation graph
- [ ] Setup and run instructions are documented and reproducible
