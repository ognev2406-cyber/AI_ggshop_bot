# services/huggingface_service.py
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
import logging

logger = logging.getLogger(__name__)


class HuggingFaceService:
    """Сервис для работы с моделями Hugging Face"""
    
    def __init__(self):
        self.model_name = "IlyaGusev/rugpt3medium_sum_gazeta"  # Русская модель
        self.tokenizer = None
        self.model = None
        self.generator = None
        self._load_model()
    
    def _load_model(self):
        """Загрузка модели"""
        try:
            logger.info(f"🔄 Загрузка модели {self.model_name}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1
            )
            
            logger.info("✅ Модель Hugging Face загружена")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели: {e}")
    
    async def generate_text(self, prompt: str, max_length: int = 200) -> str:
        """Генерация текста"""
        try:
            if not self.generator:
                return "❌ Модель не загружена"
            
            result = self.generator(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            return result[0]["generated_text"].strip()
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return f"❌ Ошибка: {str(e)}"