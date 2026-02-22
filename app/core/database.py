"""
 * Supabase Database Client Setup
 *
 * This file contains the database client singleton class and convenience
 * functions for accessing Supabase database connections.
 *
 * Public Classes:
 *    SupabaseClient
 *        Singleton class for managing Supabase client instances
 *
 * Public Functions:
 *    get_db() --> Client
 *        Returns Supabase client with anon key (for regular operations)
 *    get_service_db() --> Client
 *        Returns Supabase client with service role key (for admin operations)
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """
    Singleton Supabase client class - Manages database connections
    
    This class uses the singleton pattern to ensure only one database
    client instance is created for regular operations.
    """
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance with anon key
        
        Returns:
            Client: Supabase client instance with anon/public key
        """
        if cls._instance is None:
            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
        return cls._instance
    
    @classmethod
    def get_service_client(cls) -> Client:
        """
        Get Supabase client with service role key (for admin operations)
        
        Note: This creates a new client each time (not singleton) because
        service role key should only be used for admin operations.
        
        Returns:
            Client: Supabase client instance with service role key
        """
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )


def get_db() -> Client:
    """
    Get database client with anon key - For regular user operations
    
    Returns:
        Client: Supabase client with anon/public key
    """
    return SupabaseClient.get_client()


def get_service_db() -> Client:
    """
    Get service role database client - For admin operations only
    
    Returns:
        Client: Supabase client with service role key
    """
    return SupabaseClient.get_service_client()
