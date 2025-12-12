from .ollama_service import OllamaService, ollama_service

# Для совместимости с существующим кодом
OpenAIService = OllamaService
openai_service = ollama_service

__all__ = ['OllamaService', 'ollama_service', 'OpenAIService', 'openai_service']
from .ai_service import AIService, ai_service

__all__ = ['AIService', 'ai_service']