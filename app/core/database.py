from supabase import create_client, Client
from app.core.config import settings
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.pg_connection = None
        self._initialize_connections()

    def _initialize_connections(self):
        try:
            if settings.supabase_url and settings.supabase_key:
                self.supabase = create_client(settings.supabase_url, settings.supabase_key)
                logger.info("Supabase client initialized successfully")

            if settings.database_url:
                self.pg_connection = psycopg2.connect(
                    settings.database_url,
                    cursor_factory=RealDictCursor
                )
                logger.info("PostgreSQL connection established")

        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")

    def get_supabase(self) -> Client:
        if not self.supabase:
            raise Exception("Supabase client not initialized")
        return self.supabase

    def get_pg_connection(self):
        if not self.pg_connection:
            raise Exception("PostgreSQL connection not initialized")
        return self.pg_connection

    def close_connections(self):
        if self.pg_connection:
            self.pg_connection.close()
            logger.info("PostgreSQL connection closed")


db_manager = DatabaseManager()