"""Validate legacy adoption against the original SQL, including constraints/indexes.

The reference schema is transactional and never contains application data.
Additional columns/constraints from subsequent migrations are allowed.
"""

from uuid import uuid4

from psycopg import sql


def snapshot(connection, schema, tables):
    previous = connection.execute("SHOW search_path").fetchone()["search_path"]
    connection.execute("SELECT set_config('search_path', %s, true)", (schema,))
    try:
        result = {}
        for table in tables:
            columns = connection.execute(
                """SELECT a.attname, format_type(a.atttypid,a.atttypmod) AS type,
                a.attnotnull, a.attidentity,
                pg_get_expr(d.adbin,d.adrelid) AS default_value
                FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped""",
                (schema, table),
            ).fetchall()
            constraints = connection.execute(
                """SELECT pg_get_constraintdef(con.oid) AS definition
                FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s""",
                (schema, table),
            ).fetchall()
            indexes = connection.execute(
                """SELECT pg_get_indexdef(i.indexrelid) AS definition
                FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s AND i.indisvalid""",
                (schema, table),
            ).fetchall()
            result[table] = {
                "columns": {
                    c["attname"]: (
                        c["type"],
                        c["attnotnull"],
                        c["attidentity"],
                        c["default_value"],
                    )
                    for c in columns
                },
                "constraints": {c["definition"] for c in constraints},
                # Ignore index names and schema qualifications, retain access method and keys.
                "indexes": {i["definition"].split(" USING ", 1)[1] for i in indexes},
            }
        return result
    finally:
        connection.execute("SELECT set_config('search_path', %s, true)", (previous,))


def validate_legacy(connection, paths, current):
    """Return whether this migration has legacy artifacts; fail on partial schemas."""
    schema = connection.execute("SELECT current_schema() AS name").fetchone()["name"]
    stage = int(current.name[:3])
    tables = (
        ["tickets"]
        if stage == 1
        else ["tickets", "conversations", "conversation_messages"]
    )
    actual = snapshot(connection, schema, tables)
    if stage == 1:
        exists = bool(actual["tickets"]["columns"])
    elif stage == 2:
        exists = (
            any(actual[t]["columns"] for t in tables[1:])
            or "conversation_id" in actual["tickets"]["columns"]
        )
    else:
        exists = "title" in actual["tickets"]["columns"]
    if not exists:
        return False

    reference = "migration_reference_" + uuid4().hex
    previous = connection.execute("SHOW search_path").fetchone()["search_path"]
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(reference)))
    try:
        connection.execute("SELECT set_config('search_path', %s, true)", (reference,))
        for path in paths:
            if path.name > current.name:
                break
            connection.execute(
                path.read_text().replace("BEGIN;", "").replace("COMMIT;", "")
            )
        expected = snapshot(connection, reference, tables)
    finally:
        connection.execute("SELECT set_config('search_path', %s, true)", (previous,))
        connection.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(reference))
        )

    for table in tables:
        for column, definition in expected[table]["columns"].items():
            if actual[table]["columns"].get(column) != definition:
                raise RuntimeError(
                    f"Incompatible legacy schema for {current.name}: {table}.{column} is missing or has an unexpected type, nullability, identity or default. Restore/repair the schema before migrating; no migrations were committed."
                )
        for kind in ("constraints", "indexes"):
            if not expected[table][kind].issubset(actual[table][kind]):
                raise RuntimeError(
                    f"Incompatible legacy schema for {current.name}: {table} has missing or incompatible {kind}. Restore/repair the schema before migrating; no migrations were committed."
                )
    return True
