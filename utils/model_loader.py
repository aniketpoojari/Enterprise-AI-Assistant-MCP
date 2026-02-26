"""Model loader for the Enterprise AI Assistant."""

from typing import Any, Dict
from langchain_groq import ChatGroq

from utils.config_loader import ConfigLoader
from logger.logging import get_logger

logger = get_logger(__name__)


class ModelLoader:
    """Loads and configures language models."""

    def __init__(self, model_provider: str = "groq"):
        try:
            self.config = ConfigLoader()
            self.model_provider = model_provider.lower()
            self.llm = None
            logger.info("ModelLoader initialized")

        except Exception as e:
            error_msg = f"Error in ModelLoader Initialization -> {str(e)}"
            raise Exception(error_msg)

    def load_llm(self) -> Any:
        """Load the specified language model."""
        try:
            if self.llm is not None:
                logger.info(f"Returning cached {self.model_provider} model")
                return self.llm

            if self.model_provider == "groq":
                self.llm = self._load_groq_model()
            else:
                error_msg = f"Unsupported model provider: {self.model_provider}"
                raise Exception(error_msg)

            logger.info(f"Successfully loaded {self.model_provider} model")
            return self.llm

        except Exception as e:
            error_msg = f"Error in load_llm -> {str(e)}"
            raise Exception(error_msg)

    def _load_groq_model(self) -> ChatGroq:
        """Load Groq model."""
        try:
            api_key = self.config.get_api_key("groq")
            if not api_key:
                error_msg = "Groq API key not found. Please set GROQ_API_KEY environment variable"
                logger.error(error_msg)
                raise Exception(error_msg)

            model_name = self.config.get_env("MODEL_NAME", "llama-3.1-8b-instant")
            temperature = float(self.config.get_env("MODEL_TEMPERATURE", "0.1"))
            max_tokens = int(self.config.get_env("MODEL_MAX_TOKENS", "4096"))

            logger.info(f"Loading Groq model: {model_name}")

            return ChatGroq(
                groq_api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )

        except Exception as e:
            error_msg = f"Error in _load_groq_model -> {str(e)}"
            raise Exception(error_msg)

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        try:
            if self.llm is None:
                return {"provider": self.model_provider, "loaded": False}

            return {
                "provider": self.model_provider,
                "loaded": True,
                "model_name": getattr(self.llm, 'model_name', 'unknown'),
                "temperature": getattr(self.llm, 'temperature', 'unknown'),
                "max_tokens": getattr(self.llm, 'max_tokens', 'unknown')
            }

        except Exception as e:
            logger.error(f"Error in get_model_info -> {str(e)}")
            return {"provider": self.model_provider, "loaded": False, "error": str(e)}
