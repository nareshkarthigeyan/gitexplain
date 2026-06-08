import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from gx.services.config import (
    apply_config_environment,
    get_provider_api_key_field,
    get_user_config_path,
    load_user_config,
    update_user_config,
)

class TestConfigService(unittest.TestCase):
    def test_get_provider_api_key_field(self):
        self.assertEqual(get_provider_api_key_field("openai"), "OPENAI_API_KEY")
        self.assertEqual(get_provider_api_key_field("groq"), "GROQ_API_KEY")
        self.assertEqual(get_provider_api_key_field("openrouter"), "OPENROUTER_API_KEY")
        self.assertEqual(get_provider_api_key_field("gemini"), "GEMINI_API_KEY")
        self.assertEqual(get_provider_api_key_field("ollama"), "OLLAMA_API_KEY")
        self.assertEqual(get_provider_api_key_field("chutes"), "CHUTES_API_KEY")
        self.assertEqual(get_provider_api_key_field("anthropic"), "ANTHROPIC_API_KEY")
        self.assertEqual(get_provider_api_key_field("mistral"), "MISTRAL_API_KEY")
        self.assertEqual(get_provider_api_key_field("azure-openai"), "AZURE_OPENAI_API_KEY")
        self.assertIsNone(get_provider_api_key_field("unknown"))

    def test_apply_config_environment(self):
        original_env = os.environ.copy()
        try:
            if "LLM_PROVIDER" in os.environ:
                del os.environ["LLM_PROVIDER"]
            os.environ["OPENAI_API_KEY"] = "already-set"

            apply_config_environment({
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "from-config",
                "provider": "ignored"
            })

            self.assertEqual(os.environ.get("LLM_PROVIDER"), "openai")
            self.assertEqual(os.environ.get("OPENAI_API_KEY"), "already-set")
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_update_user_config(self):
        temp_dir = tempfile.mkdtemp()
        original_home = os.environ.get("HOME")
        original_userprofile = os.environ.get("USERPROFILE")
        try:
            os.environ["HOME"] = temp_dir
            os.environ["USERPROFILE"] = temp_dir

            res = update_user_config({
                "provider": "openai",
                "OPENAI_API_KEY": "test-key"
            })

            expected_path = os.path.join(temp_dir, ".gx", "config.json")
            self.assertEqual(res["configPath"], expected_path)
            self.assertEqual(res["config"], {
                "provider": "openai",
                "OPENAI_API_KEY": "test-key"
            })
            self.assertEqual(load_user_config(), res["config"])
            self.assertEqual(get_user_config_path(), expected_path)
        finally:
            if original_home is not None:
                os.environ["HOME"] = original_home
            else:
                os.environ.pop("HOME", None)

            if original_userprofile is not None:
                os.environ["USERPROFILE"] = original_userprofile
            else:
                os.environ.pop("USERPROFILE", None)

            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
