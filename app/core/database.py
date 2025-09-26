from supabase import create_client, Client
from app.core.config import settings
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, minconn: int = 1, maxconn: int = 5):
        self.supabase: Optional[Client] = None
        self.pg_pool: Optional[pool.SimpleConnectionPool] = None
        self.minconn = minconn
        self.maxconn = maxconn
        self._initialize_connections()

    def _initialize_connections(self):
        try:
            # Initialize Supabase client
            if settings.supabase_url and settings.supabase_key:
                self.supabase = create_client(settings.supabase_url, settings.supabase_key)
                logger.info("Supabase client initialized successfully")

            # Initialize PostgreSQL pool
            if settings.database_url:
                self.pg_pool = pool.SimpleConnectionPool(
                    self.minconn,
                    self.maxconn,
                    settings.database_url,
                    cursor_factory=RealDictCursor
                )
                if self.pg_pool:
                    logger.info("PostgreSQL connection pool established")

        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")

    def get_supabase(self) -> Client:
        if not self.supabase:
            raise Exception("Supabase client not initialized")
        return self.supabase

    def get_pg_connection(self):
        if not self.pg_pool:
            raise Exception("PostgreSQL pool not initialized")
        return self.pg_pool.getconn()

    def put_pg_connection(self, conn):
        """Return a connection back to the pool."""
        if self.pg_pool and conn:
            self.pg_pool.putconn(conn)

    def close_all_connections(self):
        if self.pg_pool:
            self.pg_pool.closeall()
            logger.info("PostgreSQL pool closed")


# Usage
db_manager = DatabaseManager()

# Example query usage
def get_current_time():
    conn = None
    try:
        conn = db_manager.get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT NOW();")
            return cur.fetchone()
    finally:
        if conn:
            db_manager.put_pg_connection(conn)
