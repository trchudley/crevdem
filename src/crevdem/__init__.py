from importlib.metadata import version

from .load import load_local, load_aws
from .datasets import get_bedmachine_geoid, get_grimp_mask
from .preprocess import (
    detrend,
    geoid_correct,
    mask_bedrock,
    mask_melange,
    get_melange_mask,
    get_sea_level,
)
from .finder import (
    find,
    bth_filter,
    threshold_depth,
    interpolate_surface,
    calc_depth,
)

__version__ = version("crevdem")
