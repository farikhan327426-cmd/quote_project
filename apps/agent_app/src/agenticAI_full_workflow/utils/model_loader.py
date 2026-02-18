import os
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

# Importing your custom project modules
from ..utils.common import read_yaml
from ..constants import config_path

# Load environment variables from .env
load_dotenv(find_dotenv(), override=True)

class ConfigLoader:
    """
    Handles loading and accessing configuration from the YAML file.
    """
    def __init__(self):
        # Using print as requested instead of logging for now
        print(f"[INFO]: Loading project configuration from {config_path}")
        self.config = read_yaml(config_path)
    
    def __getitem__(self, key):
        return self.config.get(key)

class ModelLoader(BaseModel):
    """
    Orchestrates the loading of the OpenAI LLM based on configuration.
    """
    config: Optional[ConfigLoader] = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """
        Automatically initializes the configuration after Pydantic model creation.
        """
        self.config = ConfigLoader()
    
    class Config:
        # Allows Pydantic to accept the ConfigLoader type
        arbitrary_types_allowed = True
    
    def load_llm(self, model_type: str = "default") -> ChatOpenAI:
        """
        Validates environment variables and initializes the OpenAI Chat Model.
        Args:
            model_type (str): "fast" (gpt-4o-mini), "smart" (gpt-4o), or "default".
        Returns:
            ChatOpenAI: An instance of the LangChain OpenAI wrapper.
        """
        # Retrieve API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("[ERROR]: OPENAI_API_KEY missing in .env file.")

        # Fetch model parameters from YAML config
        try:
            openai_config = self.config["llm"]["openai"]
            
            # Tiered Model Selection
            if model_type == "fast":
                model_name = openai_config.get("fast_model", "gpt-4o-mini")
            elif model_type == "smart":
                model_name = openai_config.get("smart_model", "gpt-4o")
            else:
                model_name = openai_config.get("model_name", "gpt-4o")
            
            print(f"[INFO]: Initializing OpenAI Model ({model_type}): {model_name}")
            
            return ChatOpenAI(
                model=model_name, 
                api_key=api_key,
            )
            
        except KeyError as e:
            raise KeyError(f"[ERROR]: Missing key in config.yaml: {str(e)}")
        except Exception as e:
            raise Exception(f"[ERROR]: Failed to load LLM: {str(e)}")

