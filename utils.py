import os
from pathlib import Path

from gdutils.dt import dt_str


def get_output_dir(do_makedirs:bool=True, verbose:int=0):
    dt_now = dt_str()
    OUTPUT_DIR = Path('out', dt_now).as_posix()
    if do_makedirs:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    if verbose:
        print(f"{OUTPUT_DIR=}")
    return OUTPUT_DIR
