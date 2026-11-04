"""One-off migration: the two tables behind /body (Body measurement).

  - body_weights        one weight (kg) per user per day, with how it was
                        weighed: time_of_day, weighed_at, fasted, after_bowel
  - body_measurements   tape measurements (cm) and body fat (%) per user per day

Locally `python server.py` creates the tables on its own (db.create_all()),
but the app on PythonAnywhere never runs that - so run this there BEFORE
reloading the app, or /body fails. create_all() never adds a column to a
table that already exists, so this also adds any column the model has and
the table lacks (body_weights was created before its four weighing columns).
No other table is touched.

Safe to run twice; it only creates what is missing.

    python temp/add_body_tables.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import text  # noqa: E402

from server import app  # noqa: E402
from models.db_setup import db  # noqa: E402
from models.models import BodyMeasurement, BodyWeight  # noqa: E402


def main():
    with app.app_context():
        existing = set(db.inspect(db.engine).get_table_names())
        tables = [BodyWeight.__table__, BodyMeasurement.__table__]
        db.metadata.create_all(db.engine, tables=tables, checkfirst=True)
        for table in tables:
            if table.name not in existing:
                print(f"{table.name} table created")
                continue
            print(f"{table.name} table already present")
            present = {column["name"] for column in db.inspect(db.engine).get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if not column.nullable:
                    sys.exit(f"{table.name}.{column.name} is NOT NULL - add it by hand")
                kind = column.type.compile(dialect=db.engine.dialect)
                with db.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {kind}"))
                print(f"  {table.name}.{column.name} column added ({kind})")


if __name__ == "__main__":
    main()
