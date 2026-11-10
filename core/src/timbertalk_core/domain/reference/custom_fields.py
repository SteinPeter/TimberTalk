"""Prüfung der Zusatzfelder in `attributes` gegen `custom_field_definitions`.

Neue Zusatzfelder sind Daten: eine Definition anlegen genügt, Code bleibt unverändert.
Werte werden JSON-tauglich normalisiert – Dezimalzahlen und Datumsangaben als Zeichenkette,
damit nichts verloren geht.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from timbertalk_core.context import ServiceContext
from timbertalk_core.db.types import MAX_SCALE, to_decimal
from timbertalk_core.domain.enums import CustomFieldDataType
from timbertalk_core.domain.reference.models import CustomFieldDefinition
from timbertalk_core.domain.reference.repository import CustomFieldDefinitionRepository
from timbertalk_core.errors import ValidationFailed


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise ValueError("Text erwartet.")


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Ganze Zahl erwartet, kein Wahrheitswert.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    raise ValueError("Ganze Zahl erwartet.")


def _coerce_decimal(value: Any) -> str:
    decimal_value = to_decimal(value, field="Zusatzfeld")
    exponent = decimal_value.as_tuple().exponent
    decimals = -int(exponent) if isinstance(exponent, int) and exponent < 0 else 0
    if decimals > MAX_SCALE:
        raise ValueError(f"Höchstens {MAX_SCALE} Nachkommastellen erlaubt.")
    return format(decimal_value, "f")


def _coerce_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Datum im Format JJJJ-MM-TT erwartet.") from exc
    raise ValueError("Datum im Format JJJJ-MM-TT erwartet.")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError("Wahrheitswert erwartet (true oder false).")


def _coerce_enum(value: Any, definition: CustomFieldDefinition) -> str:
    allowed = definition.enum_values or []
    text = _coerce_text(value)
    if text not in allowed:
        raise ValueError(f"Erlaubt sind: {', '.join(allowed) if allowed else 'keine Werte'}.")
    return text


def _coerce(value: Any, definition: CustomFieldDefinition) -> Any:
    data_type = CustomFieldDataType(definition.data_type)
    match data_type:
        case CustomFieldDataType.TEXT:
            return _coerce_text(value)
        case CustomFieldDataType.INT:
            return _coerce_int(value)
        case CustomFieldDataType.DECIMAL:
            return _coerce_decimal(value)
        case CustomFieldDataType.DATE:
            return _coerce_date(value)
        case CustomFieldDataType.BOOL:
            return _coerce_bool(value)
        case CustomFieldDataType.ENUM:
            return _coerce_enum(value, definition)


def validate_attributes(
    ctx: ServiceContext,
    entity_type: str,
    attributes: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prüft und normalisiert Zusatzfelder gegen die Definitionen der Entität.

    Unbekannte Schlüssel, fehlende Pflichtfelder und falsche Typen führen zu
    `ValidationFailed` mit einer Meldung je betroffenem Feld.

    Parameter:
        ctx: Aufrufkontext mit offener Session.
        entity_type: Tabellenname der Entität, z. B. `customers`.
        attributes: übergebene Zusatzfelder; `None` wird als leer behandelt.
    """
    values = dict(attributes or {})
    definitions = CustomFieldDefinitionRepository(ctx.session).for_entity_type(entity_type)
    by_key = {definition.key: definition for definition in definitions}
    errors: dict[str, str] = {}
    result: dict[str, Any] = {}

    for key, value in values.items():
        definition = by_key.get(key)
        if definition is None:
            errors[key] = (
                f"Unbekanntes Zusatzfeld '{key}' für '{entity_type}'. "
                "Bitte zuerst eine Definition in custom_field_definitions anlegen."
            )
            continue
        if value is None:
            if definition.required:
                errors[key] = f"Pflichtfeld '{definition.label_de}' darf nicht leer sein."
            continue
        try:
            result[key] = _coerce(value, definition)
        except ValueError as exc:
            errors[key] = f"{definition.label_de}: {exc}"

    for key, definition in by_key.items():
        if definition.required and key not in result:
            errors.setdefault(key, f"Pflichtfeld '{definition.label_de}' fehlt.")

    if errors:
        raise ValidationFailed(
            f"Zusatzfelder für '{entity_type}' sind ungültig.",
            errors=errors,
            entity_type=entity_type,
        )
    return result


def validate_decimal_scale(value: Decimal, decimals: int, field_de: str) -> None:
    """Prüft, dass ein Wert höchstens so viele Nachkommastellen hat wie die Einheit erlaubt.

    Parameter:
        value: zu prüfender Wert.
        decimals: erlaubte Nachkommastellen der Einheit.
        field_de: deutsche Feldbezeichnung für die Fehlermeldung.
    """
    exponent = value.as_tuple().exponent
    used = -int(exponent) if isinstance(exponent, int) and exponent < 0 else 0
    if used > decimals:
        raise ValidationFailed(
            f"{field_de}: höchstens {decimals} Nachkommastellen erlaubt, '{value}' hat {used}.",
            errors={field_de: f"höchstens {decimals} Nachkommastellen erlaubt"},
        )
