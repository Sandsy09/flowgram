"""Shared base model and validated field types for every flowgram spec."""

from collections.abc import Sequence
from typing import Annotated, TypeVar

from matplotlib.colors import is_color_like
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class Spec(BaseModel):
    """Base class for every flowgram spec model.

    Spec models are frozen, so fields cannot be reassigned after construction.
    Unknown fields are rejected, so a misspelt option fails loudly instead of
    being ignored. Build variants with ``model_copy(update=...)``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


def _check_colour(value: str) -> str:
    """Return ``value`` unchanged if matplotlib understands it as a colour.

    Args:
        value: A colour string such as ``"#2563EB"`` or ``"tab:blue"``.

    Returns:
        The same string, so the original spelling is preserved.

    Raises:
        ValueError: If matplotlib cannot parse the string as a colour.
    """
    if not is_color_like(value):
        msg = f"{value!r} is not a colour matplotlib understands"
        raise ValueError(msg)
    return value


_T = TypeVar("_T")

FrozenSeq = Annotated[Sequence[_T], AfterValidator(tuple)]
"""A sequence field that accepts any list or tuple and is stored as a tuple."""

Colour = Annotated[str, AfterValidator(_check_colour)]
"""A colour string that matplotlib can parse."""

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
"""A finite number greater than zero."""

NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
"""A finite number that is zero or greater."""
