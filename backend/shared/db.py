import hashlib
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Two Supabase projects = Two shards
SHARD_CONFIGS = {
    1: {"url": os.getenv("SHARD1_URL"), "key": os.getenv("SHARD1_ANON_KEY")},
    2: {"url": os.getenv("SHARD2_URL"), "key": os.getenv("SHARD2_ANON_KEY")}
}

def get_shard_index(store_id: str) -> int:
    """
    Deterministic sharding using SHA-256.
    Returns 1 or 2 based on hash.
    """
    hash_bytes = hashlib.sha256(store_id.encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:4], 'big')
    return 1 if (hash_int % 2 == 0) else 2

async def get_shard_connection(store_id: str):
    """
    Returns a connection to the correct Supabase shard.
    """
    shard_idx = get_shard_index(store_id)
    config = SHARD_CONFIGS[shard_idx]
    
    # Supabase requires SSL
    conn = await asyncpg.connect(
        config["url"],
        ssl="require"
    )
    return conn, shard_idx