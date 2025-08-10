"""
LLM Service with provider abstraction and cost tracking.

This service provides a unified interface for multiple LLM providers (OpenAI, Anthropic)
with advanced features including cost tracking, rate limiting, caching, and fallback strategies.
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

import httpx
from app.config import settings


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ContentTone(Enum):
    """Email content tone variations."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    tokens_used: int
    cost: float
    provider: str
    model: str
    cached: bool = False


@dataclass
class GenerationMetrics:
    """Metrics for content generation."""
    total_tokens: int
    total_cost: float
    cache_hits: int
    cache_misses: int
    api_calls: int
    average_response_time: float


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> LLMResponse:
        """Generate content using the LLM."""
        pass
    
    @abstractmethod
    def calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost for token usage."""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model for this provider."""
        pass


class OpenAIProvider(LLMProviderInterface):
    """OpenAI API provider."""
    
    # Token costs per 1K tokens (as of January 2024)
    MODEL_COSTS = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> LLMResponse:
        """Generate content using OpenAI API."""
        model = model or self.get_default_model()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional marketing content generator specializing in automotive dealership communications."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            tokens_used = data["usage"]["total_tokens"]
            cost = self.calculate_cost(tokens_used, model)
            
            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                cost=cost,
                provider="openai",
                model=model
            )
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost for OpenAI token usage."""
        if model not in self.MODEL_COSTS:
            # Use gpt-4o-mini as fallback
            model = "gpt-4o-mini"
        
        costs = self.MODEL_COSTS[model]
        # Estimate 75% input, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = tokens - input_tokens
        
        return (input_tokens * costs["input"] / 1000) + (output_tokens * costs["output"] / 1000)
    
    def get_default_model(self) -> str:
        """Get default OpenAI model."""
        return "gpt-4o-mini"


class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude API provider."""
    
    # Token costs per 1K tokens (as of January 2024)
    MODEL_COSTS = {
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> LLMResponse:
        """Generate content using Anthropic API."""
        model = model or self.get_default_model()
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": f"You are a professional marketing content generator specializing in automotive dealership communications.\n\n{prompt}"
                }
            ],
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["content"][0]["text"].strip()
            tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
            cost = self.calculate_cost(tokens_used, model)
            
            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                cost=cost,
                provider="anthropic",
                model=model
            )
    
    def calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost for Anthropic token usage."""
        if model not in self.MODEL_COSTS:
            # Use Haiku as fallback
            model = "claude-3-haiku-20240307"
        
        costs = self.MODEL_COSTS[model]
        # Estimate 75% input, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = tokens - input_tokens
        
        return (input_tokens * costs["input"] / 1000) + (output_tokens * costs["output"] / 1000)
    
    def get_default_model(self) -> str:
        """Get default Anthropic model."""
        return "claude-3-haiku-20240307"


class LLMCache:
    """Simple in-memory cache for LLM responses."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[LLMResponse, float]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key from prompt parameters."""
        content = f"{prompt}|{model}|{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, temperature: float) -> Optional[LLMResponse]:
        """Get cached response if available and not expired."""
        key = self._generate_key(prompt, model, temperature)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Return copy with cached flag set
                cached_response = LLMResponse(
                    content=response.content,
                    tokens_used=response.tokens_used,
                    cost=response.cost,
                    provider=response.provider,
                    model=response.model,
                    cached=True
                )
                return cached_response
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, prompt: str, model: str, temperature: float, response: LLMResponse):
        """Cache response with current timestamp."""
        key = self._generate_key(prompt, model, temperature)
        
        # Simple LRU: remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (response, time.time())


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 50):
        self.calls_per_minute = calls_per_minute
        self.calls: List[float] = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            # Wait until we can make another call
            oldest_call = min(self.calls)
            wait_time = 60 - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.calls.append(now)


class LLMService:
    """Main LLM service with provider abstraction and advanced features."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProviderInterface] = {}
        self.cache = LLMCache()
        self.rate_limiter = RateLimiter(calls_per_minute=50)
        self.metrics = GenerationMetrics(0, 0.0, 0, 0, 0, 0.0)
        self._response_times: List[float] = []
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers."""
        if settings.LLM_API_KEY:
            if settings.LLM_PROVIDER.lower() == "openai":
                self.providers["openai"] = OpenAIProvider(settings.LLM_API_KEY)
            elif settings.LLM_PROVIDER.lower() == "anthropic":
                self.providers["anthropic"] = AnthropicProvider(settings.LLM_API_KEY)
        
        # Add additional providers if environment variables are set
        # This allows for multiple providers to be available
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.providers["openai"] = OpenAIProvider(settings.OPENAI_API_KEY)
        
        if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            self.providers["anthropic"] = AnthropicProvider(settings.ANTHROPIC_API_KEY)
        
        if not self.providers:
            raise RuntimeError("No LLM providers configured. Please set LLM_API_KEY and LLM_PROVIDER.")
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """Generate content using specified or default provider."""
        provider = provider or settings.LLM_PROVIDER.lower()
        
        if provider not in self.providers:
            # Try fallback providers
            if self.providers:
                provider = list(self.providers.keys())[0]
            else:
                raise RuntimeError(f"Provider '{provider}' not available")
        
        llm_provider = self.providers[provider]
        model = model or llm_provider.get_default_model()
        
        # Check cache first
        if use_cache:
            cached_response = self.cache.get(prompt, model, temperature)
            if cached_response:
                self.metrics.cache_hits += 1
                return cached_response
        
        self.metrics.cache_misses += 1
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        start_time = time.time()
        
        try:
            response = await llm_provider.generate(prompt, max_tokens, temperature, model)
            
            # Update metrics
            self.metrics.total_tokens += response.tokens_used
            self.metrics.total_cost += response.cost
            self.metrics.api_calls += 1
            
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            self.metrics.average_response_time = sum(self._response_times) / len(self._response_times)
            
            # Cache the response
            if use_cache:
                self.cache.set(prompt, model, temperature, response)
            
            return response
            
        except Exception as e:
            # Try fallback provider if available
            if len(self.providers) > 1:
                fallback_providers = [p for p in self.providers.keys() if p != provider]
                for fallback_provider in fallback_providers:
                    try:
                        fallback_llm = self.providers[fallback_provider]
                        response = await fallback_llm.generate(
                            prompt, 
                            max_tokens, 
                            temperature, 
                            fallback_llm.get_default_model()
                        )
                        
                        # Update metrics
                        self.metrics.total_tokens += response.tokens_used
                        self.metrics.total_cost += response.cost
                        self.metrics.api_calls += 1
                        
                        return response
                        
                    except Exception:
                        continue
            
            raise e
    
    def get_metrics(self) -> GenerationMetrics:
        """Get current generation metrics."""
        return self.metrics
    
    def reset_metrics(self):
        """Reset generation metrics."""
        self.metrics = GenerationMetrics(0, 0.0, 0, 0, 0, 0.0)
        self._response_times.clear()
    
    def estimate_cost(self, prompt: str, provider: Optional[str] = None) -> float:
        """Estimate cost for generating content from prompt."""
        provider = provider or settings.LLM_PROVIDER.lower()
        if provider not in self.providers:
            provider = list(self.providers.keys())[0] if self.providers else "openai"
        
        # Rough estimation: 4 characters per token
        estimated_tokens = len(prompt) // 4 + 300  # Add max_tokens for output
        
        llm_provider = self.providers.get(provider)
        if llm_provider:
            return llm_provider.calculate_cost(estimated_tokens, llm_provider.get_default_model())
        else:
            return 0.01  # Default estimate


# Global service instance
llm_service = LLMService()