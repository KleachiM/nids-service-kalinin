"""Запись предсказаний в PostgreSQL."""

import os

import psycopg

from nids.schemas import Connection, Prediction


def write_prediction(connection: Connection, result: Prediction, response_time_ms: float) -> None:
    """Записать один успешный ответ API."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL не задан")
    values = connection.model_dump() | result.model_dump() | {"response_time_ms": response_time_ms}
    with psycopg.connect(database_url, connect_timeout=2) as db:
        db.execute(
            """
            INSERT INTO predictions (
                duration, protocol_type, service, flag, src_bytes, dst_bytes,
                count, srv_count, serror_rate, rerror_rate, same_srv_rate,
                diff_srv_rate, dst_host_count, dst_host_srv_count,
                prediction, probability, model_version, response_time_ms
            ) VALUES (
                %(duration)s, %(protocol_type)s, %(service)s, %(flag)s,
                %(src_bytes)s, %(dst_bytes)s, %(count)s, %(srv_count)s,
                %(serror_rate)s, %(rerror_rate)s, %(same_srv_rate)s,
                %(diff_srv_rate)s, %(dst_host_count)s, %(dst_host_srv_count)s,
                %(prediction)s, %(probability)s, %(model_version)s,
                %(response_time_ms)s
            )
            """,
            values,
        )
