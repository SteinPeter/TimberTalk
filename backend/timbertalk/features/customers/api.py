# Die Endpunkte des Features „Kunden“ unter /api/customers.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.
#
# Fachliche Fehler (CustomerError) werden hier nur in HTTP-Statuscodes übersetzt:
# nicht_gefunden → 404, ungueltig → 422, nicht_archiviert → 409.
# Falsche Kundenart oder zu lange Texte weist FastAPI selbst mit 422 ab.
#
# ruff meldet B008 bei `Depends(...)` im Parameter; CLAUDE.md schreibt genau das vor
# (so auch in den Branches von F3 und F5). Deshalb gilt die Ausnahme nur für diese Datei.
# ruff: noqa: B008

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.customers import service
from timbertalk.features.customers.models import CustomerInput, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/api/customers", tags=["Kunden"])

# Fehlercode aus service.py → HTTP-Statuscode.
ERROR_STATUS = {
    "nicht_gefunden": status.HTTP_404_NOT_FOUND,
    "ungueltig": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "nicht_archiviert": status.HTTP_409_CONFLICT,
}


def _run(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Ruft eine Service-Funktion auf und macht aus CustomerError eine HTTP-Antwort.

    Die Antwort enthält {"detail": {"code": ..., "message": ...}} mit deutscher Meldung.
    """
    try:
        return function(*args, **kwargs)
    except service.CustomerError as error:
        raise HTTPException(
            status_code=ERROR_STATUS.get(error.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": error.code, "message": str(error)},
        ) from error


@router.get("", response_model=list[CustomerRead])
def list_customers(
    q: str | None = None,
    include_archived: bool = False,
    session: Session = Depends(get_session),
):
    """Kunden alphabetisch; q sucht in Name, PLZ, Ort, Telefon und E-Mail."""
    return service.list_customers(session, query=q, include_archived=include_archived)


# Steht vor /{customer_id}, damit „export.csv“ nicht als Kundennummer gelesen wird.
@router.get("/export.csv")
def export_customers(include_archived: bool = False, session: Session = Depends(get_session)):
    """Die Kundenliste als CSV-Datei zum Herunterladen (vorläufiges Format, S-11 offen)."""
    return Response(
        content=service.export_customers_csv(session, include_archived=include_archived),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="kunden.csv"'},
    )


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: Session = Depends(get_session)):
    """Ein Kunde nach Nummer, auch archiviert."""
    return _run(service.require_customer, session, customer_id)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerInput, session: Session = Depends(get_session)):
    """Legt einen Kunden an."""
    return _run(service.create_customer, session, data)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int, changes: CustomerUpdate, session: Session = Depends(get_session)
):
    """Ändert die mitgeschickten Felder eines Kunden."""
    return _run(service.update_customer, session, customer_id, changes)


@router.post("/{customer_id}/archive", response_model=CustomerRead)
def archive_customer(customer_id: int, session: Session = Depends(get_session)):
    """Archiviert einen Kunden."""
    return _run(service.archive_customer, session, customer_id)


@router.post("/{customer_id}/restore", response_model=CustomerRead)
def restore_customer(customer_id: int, session: Session = Depends(get_session)):
    """Holt einen archivierten Kunden zurück."""
    return _run(service.restore_customer, session, customer_id)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, session: Session = Depends(get_session)) -> None:
    """Löscht einen Kunden endgültig – vorläufig nur archivierte (Steckbrief D3)."""
    _run(service.delete_customer, session, customer_id)
