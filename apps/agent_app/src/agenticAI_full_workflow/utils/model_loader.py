import os
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

# Project modules
from ..utils.common import read_yaml
from ..constants import config_path

# Load environment variables (Optional fail if not found)
load_dotenv(find_dotenv(), override=True)

class ConfigLoader:
    def __init__(self):
        print(f"[INFO]: Loading project configuration from {config_path}")
        self.config = read_yaml(config_path)
    
    def __getitem__(self, key):
        return self.config.get(key)

class ModelLoader(BaseModel):
    config: Optional[ConfigLoader] = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        self.config = ConfigLoader()
    
    class Config:
        arbitrary_types_allowed = True
    
    def load_llm(self, model_type: str = "default") -> ChatOpenAI:
        # 1. FIX: Search API Key in both .env and System Environment
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            # Container crash hone se pehle clear error message
            raise ValueError(
                "[ERROR]: OPENAI_API_KEY is missing! "
                "Please provide it via .env file or Docker environment variable (-e)."
            )

        try:
            openai_config = self.config["llm"]["openai"]
            
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