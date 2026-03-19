# Wisdom X Trends Design

## Goal

Add a reusable skill that discovers topic-specific hotspots from X/Twitter.
The skill should support user-specified topics and default to:

- finance
- tech
- ai
- economy
- regional conflicts

The output should be event-oriented rather than a flat list of tweets.

## Recommended Approach

Use `xreach search` as the runtime, then add a local aggregation layer:

1. Expand each topic into one or more search queries.
2. Fetch top and latest X results per topic.
3. Normalize tweet text and metadata.
4. De-duplicate and loosely cluster similar items.
5. Score clusters by recency + engagement + source diversity.
6. Output ranked hotspots as JSON and Markdown.

This is preferred over a pure raw-search skill because it creates reusable,
stable hotspot artifacts for downstream agents.

## Scope

First version will include:

- a new skill: `wisdom-x-trends`
- one Python script to fetch, normalize, cluster, and score
- default topic bundles
- explicit auth preflight for `xreach`
- output files under `output/x-trends/`

First version will not include:

- automatic AI summarization
- account/list-specific monitoring
- cron wiring
- sentiment analysis

## Inputs

Supported inputs:

- no topics provided -> use defaults
- explicit topics provided by name
- custom raw query strings

Config knobs:

- result count per query
- search mode (`top`, `latest`, or both)
- hours window for recency scoring
- output directory

## Output Shape

The script will emit:

- one raw JSON file with topic/query/tweet data
- one aggregated JSON file with hotspot clusters
- one Markdown report for humans

Each hotspot cluster should include:

- topic
- representative title
- cluster keywords
- tweet count
- representative tweet URLs
- recency
- engagement summary
- hotspot score

## Failure Handling

- If `xreach` is missing: fail fast with install guidance.
- If X auth is missing: fail fast with browser extraction guidance.
- If some topic queries fail: continue other topics and record partial failure.
- If no tweets are returned: output an empty but valid report.

## Verification

Verification should cover:

1. auth preflight behavior without X login
2. CLI help / argument parsing
3. one end-to-end run once X auth exists

