import os
import unittest
from unittest.mock import patch

from gx.services.ai import get_provider_config

class TestAIService(unittest.TestCase):
    def test_get_provider_config_supports_anthropic(self):
        original_api_key = os.environ.get("ANTHROPIC_API_KEY")
        original_model = os.environ.get("ANTHROPIC_MODEL")

        try:
            os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"
            os.environ["ANTHROPIC_MODEL"] = "claude-3-5-haiku-latest"

            config = get_provider_config("anthropic", None)
            self.assertEqual(config["provider"], "anthropic")
            self.assertEqual(config["apiKey"], "anthropic-key")
            self.assertEqual(config["model"], "claude-3-5-haiku-latest")
        finally:
            if original_api_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_api_key
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

            if original_model is not None:
                os.environ["ANTHROPIC_MODEL"] = original_model
            else:
                os.environ.pop("ANTHROPIC_MODEL", None)

    def test_get_provider_config_supports_mistral_and_azure_openai(self):
        original_mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        original_azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        original_azure_base_url = os.environ.get("AZURE_OPENAI_BASE_URL")
        original_azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        try:
            os.environ["MISTRAL_API_KEY"] = "mistral-key"
            os.environ["AZURE_OPENAI_API_KEY"] = "azure-key"
            os.environ["AZURE_OPENAI_BASE_URL"] = "https://demo.openai.azure.com"
            os.environ["AZURE_OPENAI_DEPLOYMENT"] = "gpt4o-mini"

            mistral = get_provider_config("mistral", None)
            azure = get_provider_config("azure-openai", None)

            self.assertEqual(mistral["provider"], "mistral")
            self.assertEqual(mistral["apiKey"], "mistral-key")
            self.assertEqual(azure["provider"], "azure-openai")
            self.assertEqual(azure["apiKey"], "azure-key")
            self.assertEqual(azure["baseUrl"], "https://demo.openai.azure.com")
            self.assertEqual(azure["deployment"], "gpt4o-mini")
        finally:
            if original_mistral_api_key is not None:
                os.environ["MISTRAL_API_KEY"] = original_mistral_api_key
            else:
                os.environ.pop("MISTRAL_API_KEY", None)

            if original_azure_api_key is not None:
                os.environ["AZURE_OPENAI_API_KEY"] = original_azure_api_key
            else:
                os.environ.pop("AZURE_OPENAI_API_KEY", None)

            if original_azure_base_url is not None:
                os.environ["AZURE_OPENAI_BASE_URL"] = original_azure_base_url
            else:
                os.environ.pop("AZURE_OPENAI_BASE_URL", None)

            if original_azure_deployment is not None:
                os.environ["AZURE_OPENAI_DEPLOYMENT"] = original_azure_deployment
            else:
                os.environ.pop("AZURE_OPENAI_DEPLOYMENT", None)

if __name__ == "__main__":
    unittest.main()
