"""Shared base model and validated field types for every flowgram spec."""

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, Self, TypeVar

from matplotlib.colors import is_color_like
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)


class Spec(BaseModel):
    """Base class for every flowgram spec model.

    Spec models are frozen, so fields cannot be reassigned after construction.
    Unknown fields are rejected, so a misspelt option fails loudly instead of
    being ignored. Build variants with ``model_copy(update=...)``, which checks
    the result just as construction does.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_serializer(mode="wrap")
    def _keep_kind(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Any:
        """Dump the spec, keeping its ``kind`` when defaults are left out.

        ``kind`` has a default, so ``exclude_defaults`` and ``exclude_unset``
        would drop it, and the dump would no longer load: unions pick their
        member by ``kind``. It is put back first, unless asked to be excluded.
        """
        data = handler(self)
        kind = getattr(self, "kind", None)
        if (
            isinstance(data, dict)
            and isinstance(kind, str)
            and "kind" not in data
            and (info.exclude_defaults or info.exclude_unset)
            and not _excludes_kind(info.exclude)
        ):
            data = {"kind": kind, **data}
        return data

    def model_copy(
        self, *, update: Mapping[str, Any] | None = None, deep: bool = False
    ) -> Self:
        """Return a copy of the spec, with ``update`` applied and checked.

        Unlike plain Pydantic, a copy with ``update`` is built again through
        ``model_validate``, so a bad value, an unknown field or a broken
        reference raises the same ``ValidationError`` as building the spec
        from scratch, with every problem listed. Values in ``update`` may be
        specs or plain data, such as a dict with a ``kind``. Nested specs that
        are not updated are reused as they are, since they were checked when
        they were built.

        Args:
            update: Field values to change in the copy.
            deep: Copy nested values too, rather than sharing them.

        Returns:
            The new spec.

        Raises:
            pydantic.ValidationError: If the updated spec is not valid.
        """
        if not update:
            return super().model_copy(deep=deep)
        data = {name: getattr(self, name) for name in self.model_fields_set}
        data.update(update)
        copy = self.model_validate(data)
        return super(Spec, copy).model_copy(deep=True) if deep else copy


def _excludes_kind(exclude: object) -> bool:
    """Return whether a dump's ``exclude`` argument names ``kind``."""
    return isinstance(exclude, set | frozenset | dict) and "kind" in exclude


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

Finite = Annotated[float, Field(allow_inf_nan=False)]
"""A finite number, which may be negative."""

Opacity = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
"""An opacity from 0 (invisible) to 1 (solid)."""

TextAlign = Literal["left", "center", "right"]
"""Horizontal alignment of text lines."""

TextVAlign = Literal["top", "center"]
"""Vertical placement of a box's text: at the top, or centred."""

FontWeight = Literal["normal", "bold"]
"""Weight of a line of text."""
