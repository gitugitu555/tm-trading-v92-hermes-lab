# V9.2 Tier-2 Bar Data Integrity Review

## Summary

The Tier-2 cache builder had a provenance risk around `is_buyer_maker` parsing. If that field was ingested as a string and used directly in `pl.when(pl.col("is_buyer_maker"))`, the signed quantity logic could be inverted or otherwise corrupted, which would in turn corrupt `volume_delta` in the generated bars.

## Files Changed

- [scripts/v92_tier2_cache_builder.py](/home/tokio/tm-trading-v92-core/scripts/v92_tier2_cache_builder.py)
- [tests/test_v92_tier2_cache_builder.py](/home/tokio/tm-trading-v92-core/tests/test_v92_tier2_cache_builder.py)

## Why `volume_delta` May Have Been Corrupted

`volume_delta` is derived from signed trade quantity. If `is_buyer_maker` is not normalized to a real boolean before sign assignment, then string values, mixed representations, or other malformed payloads can lead to incorrect signed quantity aggregation. That contaminates the bar-level `volume_delta` field and any downstream research that depends on it.

## Why Existing C Diagnostics Still Matter

The C_ExhaustionFade replay diagnostics remain useful as replay research because they test the repaired strategy path against the current bar files. However, those diagnostics depend on the integrity of the Tier-2 bar provenance. If the underlying 750 BTC bars were built with a corrupted signed-flow field, the diagnostics are still informative about replay mechanics, but they do not fully establish bar provenance correctness.

## Production Evidence Note

The current C anchor should not be treated as final production evidence until the existing 750 BTC bars are sanity-checked or regenerated with the hardened Tier-2 builder path.

## Next Required Task

Run a read-only sanity check on the existing `/bars_750btc` outputs before deciding whether full regeneration is required.
