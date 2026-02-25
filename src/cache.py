import json
import os
import hashlib

CACHE_PATH = "data/cache/cache.json"

os.makedirs("data/cache", exist_ok=True)

def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def _save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)

def _hash_text(text):
    return hashlib.md5(text.encode()).hexdigest()

def get_cached_result(text):
    cache = _load_cache()
    key = _hash_text(text)
    return cache.get(key)

def store_cached_result(text, result):
    cache = _load_cache()
    key = _hash_text(text)
    cache[key] = result
    _save_cache(cache)