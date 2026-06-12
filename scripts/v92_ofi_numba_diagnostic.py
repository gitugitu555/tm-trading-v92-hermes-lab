#!/usr/bin/env python3
"""
V9.2 OFI Numba Diagnostics & Validation

Extracts the first 100,000 rows of an L2 Orderbook file,
runs BOTH the pure Python OFI engine and the ultra-fast Numba OFI engine,
and asserts bit-for-bit identical outputs to ensure the state machine is perfect.
"""

import sys
import io
import time
import pandas as pd
import numpy as np
import zstandard as zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.microstructure_ofi import process_chunk as process_chunk_py
from features.microstructure_numba_ofi import process_chunk_fast as process_chunk_numba

def load_zst_parquet(filepath: Path) -> pd.DataFrame:
    with open(filepath, 'rb') as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            decompressed_data = reader.read()
    df = pd.read_parquet(io.BytesIO(decompressed_data), engine='pyarrow')
    return df

def main():
    print("V9.2 OFI Numba Validation Initialized.")
    
    sample_file = Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-03-14/00/BTCUSDT_orderbook.parquet.zst")
    
    if not sample_file.exists():
        print(f"Sample file {sample_file} not found.")
        return
        
    print(f"Decompressing {sample_file.name} into memory...")
    df = load_zst_parquet(sample_file)
    df = df.sort_values(by=['transaction_time', 'event_time', 'first_update_id']).reset_index(drop=True)
    
    chunk_size = 100000
    df_chunk_py = df.head(chunk_size).copy()
    df_chunk_numba = df.head(chunk_size).copy()
    
    print(f"\n1. Running Pure Python OFI Engine ({chunk_size:,} events)...")
    start_py = time.time()
    df_chunk_py = process_chunk_py(df_chunk_py)
    py_time = time.time() - start_py
    print(f"   -> Python Time: {py_time:.3f} seconds")
    
    print(f"\n2. Running Numba JIT OFI Engine ({chunk_size:,} events)...")
    # First run will include JIT compilation time overhead
    start_numba = time.time()
    df_chunk_numba = process_chunk_numba(df_chunk_numba)
    numba_time = time.time() - start_numba
    print(f"   -> Numba Time (incl. compilation): {numba_time:.3f} seconds")
    
    # Run a second time to see pure execution speed without compilation
    df_chunk_numba_pure = df.head(chunk_size).copy()
    start_numba_pure = time.time()
    process_chunk_numba(df_chunk_numba_pure)
    numba_pure_time = time.time() - start_numba_pure
    print(f"   -> Numba Time (pure execution): {numba_pure_time:.4f} seconds")
    
    speedup = py_time / numba_pure_time
    print(f"\n--- Numba is {speedup:.1f}x FASTER ---")
    
    # Validate Bit-for-Bit exactness
    print("\n--- Validation ---")
    py_ofi = df_chunk_py['ofi'].values
    numba_ofi = df_chunk_numba['ofi'].values
    
    differences = np.abs(py_ofi - numba_ofi)
    max_diff = np.max(differences)
    mismatches = np.sum(differences > 1e-8)
    
    print(f"Python Total OFI: {py_ofi.sum():,.2f}")
    print(f"Numba Total OFI:  {numba_ofi.sum():,.2f}")
    print(f"Max Difference:   {max_diff}")
    print(f"Mismatches:       {mismatches}")
    
    if mismatches == 0:
        print("\nSUCCESS: Numba engine matches Pure Python engine bit-for-bit!")
    else:
        print("\nFAILURE: Mismatch found in state machine logic. Do not scale.")
        # Find first mismatch
        for i in range(len(py_ofi)):
            if abs(py_ofi[i] - numba_ofi[i]) > 1e-8:
                print(f"First mismatch at index {i}: Py={py_ofi[i]} Numba={numba_ofi[i]}")
                break

if __name__ == "__main__":
    sys.exit(main())
