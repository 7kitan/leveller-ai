"""
Prompt Manager - Simple LLM prompt template management with Redis caching
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List
import redis

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Simple prompt manager with Redis caching.
    Loads active prompts to Redis and provides parameter replacement.
    """
    
    def __init__(self, redis_client: redis.Redis, db_session_factory=None):
        """
        Initialize PromptManager
        
        Args:
            redis_client: Redis client for caching
            db_session_factory: Factory function to create database sessions
        """
        self.redis = redis_client
        self.db_session_factory = db_session_factory
        self.cache_prefix = "prompt:"
    
    def _get_cache_key(self, prompt_key: str) -> str:
        """Generate Redis cache key for a prompt"""
        return f"{self.cache_prefix}{prompt_key}"
    
    def load_active_prompts_to_redis(self) -> int:
        """
        Load all active prompts from database to Redis.
        Called on startup.
        
        Returns:
            Number of prompts loaded
        """
        if not self.db_session_factory:
            logger.error("Database session factory not configured")
            return 0
        
        try:
            from sqlalchemy import text
            with self.db_session_factory() as session:
                query = text("""
                    SELECT category, name, prompt_text, parameters, model_config
                    FROM prompt_templates
                    WHERE is_active = true
                """)
                results = session.execute(query).fetchall()
                
                count = 0
                for row in results:
                    category = row[0]
                    data = {
                        "name": row[1],
                        "text": row[2],
                        "parameters": row[3] if isinstance(row[3], list) else json.loads(row[3] or "[]"),
                        "model_config": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
                    }
                    
                    cache_key = self._get_cache_key(category)
                    self.redis.set(cache_key, json.dumps(data))
                    count += 1
                    logger.debug(f"Loaded prompt '{category}' to Redis")
                
                logger.info(f"Loaded {count} active prompts to Redis")
                return count
                
        except Exception as e:
            logger.error(f"Error loading prompts to Redis: {e}")
            return 0
    
    def get_prompt_data(self, prompt_category: str) -> Optional[Dict[str, Any]]:
        """
        Get prompt data from Redis or database.
        
        Args:
            prompt_category: Prompt category (e.g., 'cv_parsing')
            
        Returns:
            Dict with 'text', 'parameters', 'model_config' or None
        """
        cache_key = self._get_cache_key(prompt_category)
        
        # Try Redis first
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                logger.debug(f"Loaded prompt '{prompt_category}' from Redis cache")
                return data
        except Exception as e:
            logger.warning(f"Redis cache read error for '{prompt_category}': {e}")
        
        # Fallback to database
        if not self.db_session_factory:
            logger.error("Database session factory not configured")
            return None
        
        try:
            from sqlalchemy import text
            with self.db_session_factory() as session:
                query = text("""
                    SELECT name, prompt_text, parameters, model_config
                    FROM prompt_templates
                    WHERE category = :category AND is_active = true
                    LIMIT 1
                """)
                result = session.execute(query, {"category": prompt_category}).fetchone()
                
                if result:
                    data = {
                        "name": result[0],
                        "text": result[1],
                        "parameters": result[2] if isinstance(result[2], list) else json.loads(result[2] or "[]"),
                        "model_config": result[3] if isinstance(result[3], dict) else json.loads(result[3] or "{}")
                    }
                    
                    # Cache it for next time
                    try:
                        self.redis.set(cache_key, json.dumps(data))
                    except Exception as e:
                        logger.warning(f"Failed to cache prompt '{prompt_category}': {e}")
                    
                    logger.debug(f"Loaded prompt '{prompt_category}' from database")
                    return data
                
                logger.error(f"Active prompt '{prompt_category}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error loading prompt from database: {e}")
            return None
    
    def render_prompt(self, prompt_category: str, **params) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Get and render a prompt template with parameters.
        
        Args:
            prompt_category: Prompt category (e.g., 'cv_parsing')
            **params: Parameters to replace in template
            
        Returns:
            Tuple of (rendered_prompt, model_config) or (None, None) if not found
        """
        data = self.get_prompt_data(prompt_category)
        if not data:
            return None, None
        
        template = data["text"]
        
        # Replace parameters: {{param}} → value
        for param_name, param_value in params.items():
            placeholder = f"{{{{{param_name}}}}}"
            template = template.replace(placeholder, str(param_value))
        
        # Check for unreplaced parameters (warning only)
        unreplaced = re.findall(r'\{\{(\w+)\}\}', template)
        if unreplaced:
            logger.warning(f"Prompt '{prompt_category}' has unreplaced parameters: {unreplaced}")
        
        logger.info(f"Rendered prompt '{prompt_category}' with {len(params)} parameters")
        return template, data["model_config"]
    
    def invalidate_cache(self, prompt_category: str) -> bool:
        """
        Invalidate cached prompt.
        Call this after updating a prompt.
        
        Args:
            prompt_category: Prompt category to invalidate
            
        Returns:
            True if cache was invalidated
        """
        try:
            cache_key = self._get_cache_key(prompt_category)
            deleted = self.redis.delete(cache_key)
            logger.info(f"Invalidated cache for prompt '{prompt_category}': {deleted > 0}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Error invalidating cache for '{prompt_category}': {e}")
            return False
    
    def reload_prompt(self, prompt_category: str) -> bool:
        """
        Reload a specific prompt from database to Redis.
        
        Args:
            prompt_category: Prompt category to reload
            
        Returns:
            True if successfully reloaded
        """
        if not self.db_session_factory:
            return False
        
        try:
            from sqlalchemy import text
            with self.db_session_factory() as session:
                query = text("""
                    SELECT name, prompt_text, parameters, model_config
                    FROM prompt_templates
                    WHERE category = :category AND is_active = true
                    LIMIT 1
                """)
                result = session.execute(query, {"category": prompt_category}).fetchone()
                
                if result:
                    data = {
                        "name": result[0],
                        "text": result[1],
                        "parameters": result[2] if isinstance(result[2], list) else json.loads(result[2] or "[]"),
                        "model_config": result[3] if isinstance(result[3], dict) else json.loads(result[3] or "{}")
                    }
                    
                    cache_key = self._get_cache_key(prompt_category)
                    self.redis.set(cache_key, json.dumps(data))
                    logger.info(f"Reloaded prompt '{prompt_category}' to Redis")
                    return True
                
                logger.warning(f"Active prompt '{prompt_category}' not found for reload")
                return False
                
        except Exception as e:
            logger.error(f"Error reloading prompt '{prompt_category}': {e}")
            return False
    
    def reload_prompt(self, prompt_key: str) -> bool:
        """
        Reload a specific prompt from database to Redis.
        
        Args:
            prompt_key: Prompt key to reload
            
        Returns:
            True if successfully reloaded
        """
        if not self.db_session_factory:
            return False
        
        try:
            from sqlalchemy import text
            with self.db_session_factory() as session:
                query = text("""
                    SELECT name, prompt_text, parameters, model_config
                    FROM prompt_templates
                    WHERE key = :key AND is_active = true
                    LIMIT 1
                """)
                result = session.execute(query, {"key": prompt_key}).fetchone()
                
                if result:
                    data = {
                        "name": result[0],
                        "text": result[1],
                        "parameters": result[2] if isinstance(result[2], list) else json.loads(result[2] or "[]"),
                        "model_config": result[3] if isinstance(result[3], dict) else json.loads(result[3] or "{}")
                    }
                    
                    cache_key = self._get_cache_key(prompt_key)
                    self.redis.set(cache_key, json.dumps(data))
                    logger.info(f"Reloaded prompt '{prompt_key}' to Redis")
                    return True
                else:
                    # No active prompt found, remove from cache
                    self.invalidate_cache(prompt_key)
                    logger.info(f"No active prompt '{prompt_key}' found, removed from cache")
                    return False
                    
        except Exception as e:
            logger.error(f"Error reloading prompt '{prompt_key}': {e}")
            return False


# Global instance
_prompt_manager: Optional[PromptManager] = None


def init_prompt_manager(redis_client: redis.Redis, db_session_factory=None):
    """Initialize the global prompt manager instance"""
    global _prompt_manager
    _prompt_manager = PromptManager(redis_client, db_session_factory)
    logger.info("Prompt manager initialized")
    
    # Load active prompts to Redis
    count = _prompt_manager.load_active_prompts_to_redis()
    logger.info(f"Loaded {count} active prompts on startup")


def get_prompt_manager() -> Optional[PromptManager]:
    """Get the global prompt manager instance"""
    return _prompt_manager


def get_prompt(prompt_key: str, **params) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Convenience function to render a prompt using the global manager.
    
    Args:
        prompt_key: Prompt key (e.g., 'cv_parsing')
        **params: Parameters to replace in template
        
    Returns:
        Tuple of (rendered_prompt, model_config) or (None, None)
        
    Example:
        prompt, config = get_prompt('cv_parsing', 
                                    cv_text=cv_content, 
                                    current_date='2026-05-03')
    """
    if not _prompt_manager:
        logger.error("Prompt manager not initialized. Call init_prompt_manager() first.")
        return None, None
    
    return _prompt_manager.render_prompt(prompt_key, **params)
