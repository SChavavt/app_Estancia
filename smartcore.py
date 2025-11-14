import numpy as np

try:
    WORLD_TIMESTAMPS = np.load("world_timestamps.npy")
except Exception:
    WORLD_TIMESTAMPS = None


def buscar_frame(timestamp_segundos):
    if WORLD_TIMESTAMPS is None:
        return None
    if timestamp_segundos is None:
        return None
    try:
        idx = np.searchsorted(WORLD_TIMESTAMPS, timestamp_segundos)
        return int(idx)
    except Exception:
        return None
