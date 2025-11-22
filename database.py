# database.py
import mysql.connector
from mysql.connector import pooling, Error
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.database = os.getenv('DB_NAME', 'hotelReservation_db')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASS', 'Hashedword1!')
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="hotel_pool",
                pool_size=5,
                pool_reset_session=True,
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                use_unicode=True
            )
        except Error as e:
            logger.exception("Error creating pool: %s", e)
            self.pool = None

    def _get_conn(self):
        if not self.pool:
            raise RuntimeError("Connection pool not available. Check DB settings.")
        return self.pool.get_connection()

    def fetch_all(self, query, params=None):
        conn = None; cursor = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Exception as e:
            logger.exception("fetch_all error: %s", e)
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def fetch_one(self, query, params=None):
        conn = None; cursor = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except Exception as e:
            logger.exception("fetch_one error: %s", e)
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def execute(self, query, params=None, commit=True):
        conn = None; cursor = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.exception("execute error: %s", e)
            if conn: conn.rollback()
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def executemany(self, query, seq_of_params, commit=True):
        conn = None; cursor = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.executemany(query, seq_of_params)
            if commit:
                conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.exception("executemany error: %s", e)
            if conn: conn.rollback()
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

# singleton instance
db = Database()
