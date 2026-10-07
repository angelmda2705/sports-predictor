"""Actualiza los datos (Mundial + ligas) si están viejos. Pensado para correr al abrir la app.

- Si el snapshot tiene menos de N horas, no hace nada (evita re-descargar de más).
- Con ``--force`` actualiza siempre.
- Al actualizar con éxito, borra el historial (SQLite) para que se recalcule con
  los datos nuevos en el próximo arranque del backend.
- Si no hay internet o algo falla, CONSERVA los datos previos (no rompe la app).

Uso: python -m scripts.refresh_data [--force]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.ingestion.snapshot import default_snapshot_path  # noqa: E402

FRESH_HOURS = 3.0


def main() -> None:
    force = "--force" in sys.argv
    snapshot = default_snapshot_path()

    if not force and snapshot.exists():
        age_h = (time.time() - snapshot.stat().st_mtime) / 3600.0
        if age_h < FRESH_HOURS:
            print(f"Datos recientes ({age_h:.1f} h). No se actualiza. (usa --force para forzar)")
            return

    print("Actualizando datos del Mundial y ligas (openfootball)...")
    from scripts.ingest_real import main as ingest

    try:
        ingest()
    except SystemExit as exc:
        if exc.code:
            print("No se pudo actualizar (¿sin internet?). Se conservan los datos previos.")
            return
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo actualizar: {exc}. Se conservan los datos previos.")
        return

    # Éxito: reiniciar el historial para que se recalcule con los datos nuevos.
    history_db = snapshot.parent.parent / "sports_predictor.db"
    try:
        if history_db.exists():
            history_db.unlink()
            print("Historial reiniciado; se recalculará al arrancar el backend.")
    except OSError:
        # Probablemente el backend está abierto y tiene el archivo bloqueado.
        print("Aviso: cierra la app antes de actualizar para reiniciar el historial.")


if __name__ == "__main__":
    main()
