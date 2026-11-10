"""Geschäftslogik für Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

import uuid
from datetime import date

from timbertalk_core.clock import today
from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.company.models import Company, Setting, TaxRate
from timbertalk_core.domain.company.repository import (
    CompanyRepository,
    SettingRepository,
    TaxRateRepository,
)
from timbertalk_core.domain.company.schemas import (
    CompanyRead,
    CompanyUpsert,
    SettingRead,
    SettingUpsert,
    TaxRateCreate,
    TaxRateRead,
    TaxRateUpdate,
)
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    require_found,
)

COMPANY_DE = "Firmendaten"
SETTING_DE = "Einstellung"
TAX_RATE_DE = "Steuersatz"


# --------------------------------------------------------------------------- Firmendaten


@operation(name="company.set", read_only=False, summary_de="Legt die Firmendaten an oder ändert sie.")
def set_company(ctx: ServiceContext, data: CompanyUpsert, expected_version: int | None = None) -> CompanyRead:
    """Legt die Firmendaten an oder ändert den vorhandenen Datensatz.

    Es gibt genau einen aktiven Firmendatensatz; ein zweiter wird nicht angelegt.

    Parameter:
        data: Name, Adresse, Steuer- und Bankangaben sowie Standort des Betriebs.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CompanyRepository(ctx.session)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, Company.__tablename__, values["attributes"])
    existing = repository.current()
    if existing is None:
        company = repository.add(Company(**values))
    else:
        check_version(existing, expected_version, COMPANY_DE)
        for field, value in values.items():
            setattr(existing, field, value)
        company = existing
    ctx.session.flush()
    return CompanyRead.model_validate(company)


@operation(name="company.get", read_only=True, summary_de="Liest die Firmendaten.")
def get_company(ctx: ServiceContext) -> CompanyRead:
    """Liest die Firmendaten des Betriebs."""
    company = CompanyRepository(ctx.session).current()
    if company is None:
        raise NotFound("Es sind noch keine Firmendaten hinterlegt.", entity_type="company")
    return CompanyRead.model_validate(company)


# --------------------------------------------------------------------------- Einstellungen


@operation(name="setting.set", read_only=False, summary_de="Setzt eine Einstellung.")
def set_setting(ctx: ServiceContext, data: SettingUpsert) -> SettingRead:
    """Setzt eine Einstellung; ein vorhandener Schlüssel wird überschrieben.

    Parameter:
        data: Schlüssel, Wert (JSON) und optionaler Anzeigename.
    """
    repository = SettingRepository(ctx.session)
    existing = repository.by_key(data.key)
    if existing is None:
        setting = repository.add(Setting(**data.model_dump()))
    else:
        existing.value = data.value
        if data.label_de is not None:
            existing.label_de = data.label_de
        setting = existing
    ctx.session.flush()
    return SettingRead.model_validate(setting)


@operation(name="setting.get", read_only=True, summary_de="Liest eine Einstellung.")
def get_setting(ctx: ServiceContext, key: str) -> SettingRead:
    """Liest eine Einstellung anhand ihres Schlüssels.

    Parameter:
        key: Schlüssel der Einstellung, z. B. `default_hourly_rate`.
    """
    setting = SettingRepository(ctx.session).by_key(key)
    if setting is None:
        raise NotFound(f"Die Einstellung '{key}' ist nicht hinterlegt.", key=key)
    return SettingRead.model_validate(setting)


@operation(name="setting.list", read_only=True, summary_de="Listet alle Einstellungen.")
def list_settings(ctx: ServiceContext, limit: int = 50, offset: int = 0) -> Page[SettingRead]:
    """Listet Einstellungen mit Paging.

    Parameter:
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    return build_page(
        SettingRepository(ctx.session),
        SettingRead,
        order_by=[Setting.key],
        limit=limit,
        offset=offset,
    )


@operation(name="setting.delete", read_only=False, summary_de="Löscht eine Einstellung (Soft Delete).")
def delete_setting(ctx: ServiceContext, key: str) -> SettingRead:
    """Markiert eine Einstellung als gelöscht.

    Parameter:
        key: Schlüssel der Einstellung.
    """
    repository = SettingRepository(ctx.session)
    setting = repository.by_key(key)
    if setting is None:
        raise NotFound(f"Die Einstellung '{key}' ist nicht hinterlegt.", key=key)
    repository.soft_delete(setting)
    ctx.session.flush()
    return SettingRead.model_validate(setting)


# --------------------------------------------------------------------------- Steuersätze


def _check_tax_rate_period(
    repository: TaxRateRepository,
    code: str,
    valid_from: date,
    valid_to: date | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Weist überlappende Gültigkeiten für denselben Steuersatz-Code ab."""
    if valid_to is not None and valid_to < valid_from:
        raise ValidationFailed(
            "Das Ende der Gültigkeit darf nicht vor dem Beginn liegen.",
            errors={"valid_to": "muss nach valid_from liegen"},
        )
    for existing in repository.by_code(code):
        if exclude_id is not None and existing.id == exclude_id:
            continue
        other_end = existing.valid_to
        overlaps = (other_end is None or other_end >= valid_from) and (
            valid_to is None or existing.valid_from <= valid_to
        )
        if overlaps:
            raise Conflict(
                f"Der Steuersatz '{code}' hat bereits einen überlappenden "
                f"Gültigkeitszeitraum ab {existing.valid_from.isoformat()}.",
                code=code,
                conflicting_id=str(existing.id),
            )


@operation(name="tax_rate.create", read_only=False, summary_de="Legt einen Steuersatz an.")
def create_tax_rate(ctx: ServiceContext, data: TaxRateCreate) -> TaxRateRead:
    """Legt einen Steuersatz mit Gültigkeitszeitraum an.

    Parameter:
        data: Code, Prozentsatz, Anzeigename und Gültigkeitszeitraum.
    """
    repository = TaxRateRepository(ctx.session)
    _check_tax_rate_period(repository, data.code, data.valid_from, data.valid_to)
    tax_rate = repository.add(TaxRate(**data.model_dump()))
    ctx.session.flush()
    return TaxRateRead.model_validate(tax_rate)


@operation(name="tax_rate.get", read_only=True, summary_de="Liest einen Steuersatz.")
def get_tax_rate(ctx: ServiceContext, tax_rate_id: uuid.UUID) -> TaxRateRead:
    """Liest einen Steuersatz anhand seiner Kennung.

    Parameter:
        tax_rate_id: Kennung des Steuersatzes.
    """
    tax_rate = require_found(TaxRateRepository(ctx.session).get(tax_rate_id), TAX_RATE_DE, tax_rate_id)
    return TaxRateRead.model_validate(tax_rate)


@operation(
    name="tax_rate.get_for_date",
    read_only=True,
    summary_de="Liest den an einem Tag gültigen Steuersatz.",
)
def get_tax_rate_for_date(ctx: ServiceContext, code: str, on_date: date | None = None) -> TaxRateRead:
    """Liefert den Steuersatz, der an einem Tag gültig ist.

    Parameter:
        code: Code des Steuersatzes, z. B. `19`.
        on_date: Stichtag; ohne Angabe gilt der heutige Tag.
    """
    stichtag = on_date or today()
    for tax_rate in TaxRateRepository(ctx.session).by_code(code):
        if tax_rate.valid_from <= stichtag and (tax_rate.valid_to is None or tax_rate.valid_to >= stichtag):
            return TaxRateRead.model_validate(tax_rate)
    raise NotFound(
        f"Für den Steuersatz '{code}' ist am {stichtag.isoformat()} kein Wert gültig.",
        code=code,
        on_date=stichtag.isoformat(),
    )


@operation(name="tax_rate.list", read_only=True, summary_de="Listet Steuersätze.")
def list_tax_rates(
    ctx: ServiceContext, code: str | None = None, limit: int = 50, offset: int = 0
) -> Page[TaxRateRead]:
    """Listet Steuersätze mit Paging, optional nach Code gefiltert.

    Parameter:
        code: Code des Steuersatzes.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = [TaxRate.code == code] if code is not None else []
    return build_page(
        TaxRateRepository(ctx.session),
        TaxRateRead,
        filters=filters,
        order_by=[TaxRate.code, TaxRate.valid_from],
        limit=limit,
        offset=offset,
    )


@operation(name="tax_rate.update", read_only=False, summary_de="Ändert einen Steuersatz.")
def update_tax_rate(
    ctx: ServiceContext,
    tax_rate_id: uuid.UUID,
    data: TaxRateUpdate,
    expected_version: int | None = None,
) -> TaxRateRead:
    """Ändert einen Steuersatz; überlappende Gültigkeiten werden abgewiesen.

    Parameter:
        tax_rate_id: Kennung des Steuersatzes.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = TaxRateRepository(ctx.session)
    tax_rate = require_found(repository.get(tax_rate_id), TAX_RATE_DE, tax_rate_id)
    check_version(tax_rate, expected_version, TAX_RATE_DE)
    changes = data.model_dump(exclude_unset=True)
    neuer_beginn = changes.get("valid_from", tax_rate.valid_from)
    neues_ende = changes.get("valid_to", tax_rate.valid_to)
    if "valid_from" in changes or "valid_to" in changes:
        _check_tax_rate_period(repository, tax_rate.code, neuer_beginn, neues_ende, exclude_id=tax_rate.id)
    apply_updates(tax_rate, data)
    ctx.session.flush()
    return TaxRateRead.model_validate(tax_rate)


@operation(name="tax_rate.delete", read_only=False, summary_de="Löscht einen Steuersatz (Soft Delete).")
def delete_tax_rate(
    ctx: ServiceContext, tax_rate_id: uuid.UUID, expected_version: int | None = None
) -> TaxRateRead:
    """Markiert einen Steuersatz als gelöscht.

    Parameter:
        tax_rate_id: Kennung des Steuersatzes.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = TaxRateRepository(ctx.session)
    tax_rate = require_found(repository.get(tax_rate_id), TAX_RATE_DE, tax_rate_id)
    check_version(tax_rate, expected_version, TAX_RATE_DE)
    repository.soft_delete(tax_rate)
    ctx.session.flush()
    return TaxRateRead.model_validate(tax_rate)
