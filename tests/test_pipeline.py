import json
import os
import shutil
import tempfile
import unittest

from gx.services.pipeline import (
    build_ci_workflow,
    format_pipeline_recommendations,
    inspect_repository_for_pipeline,
    resolve_pipeline_selection,
    write_pipeline_files,
)

class TestPipelineService(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def test_inspect_repository_for_pipeline_node(self):
        with open(os.path.join(self.cwd, "package.json"), "w", encoding="utf-8") as f:
            json.dump({
                "name": "demo-cli",
                "version": "1.0.0",
                "scripts": {
                    "lint": "node --check index.js",
                    "test": "node --test",
                    "build": "node build.js"
                }
            }, f, indent=2)
        with open(os.path.join(self.cwd, "package-lock.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        analysis = inspect_repository_for_pipeline(self.cwd)

        self.assertTrue(analysis["supported"])
        self.assertEqual(analysis["primary"]["type"], "node")
        self.assertEqual(analysis["primary"]["packageManager"], "npm")
        self.assertEqual(analysis["primary"]["commands"]["lint"], "npm run lint")
        self.assertEqual(analysis["primary"]["commands"]["test"], "npm test")
        self.assertEqual(analysis["primary"]["commands"]["build"], "npm run build")
        self.assertEqual(analysis["primary"]["commands"]["pack"], "npm pack --dry-run")

    def test_inspect_repository_for_pipeline_android(self):
        with open(os.path.join(self.cwd, "settings.gradle.kts"), "w", encoding="utf-8") as f:
            f.write('rootProject.name = "launch"\ninclude(":app")\n')
        with open(os.path.join(self.cwd, "build.gradle.kts"), "w", encoding="utf-8") as f:
            f.write("plugins {}\n")
        with open(os.path.join(self.cwd, "gradlew"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
        
        os.makedirs(os.path.join(self.cwd, "app"), exist_ok=True)
        with open(os.path.join(self.cwd, "app", "build.gradle.kts"), "w", encoding="utf-8") as f:
            f.write("\n".join([
                "plugins {",
                "  alias(libs.plugins.android.application)",
                "  alias(libs.plugins.kotlin.android)",
                "}",
                "",
                "android {",
                '  namespace = "com.example.launch"',
                "}"
            ]))

        analysis = inspect_repository_for_pipeline(self.cwd)

        self.assertTrue(analysis["supported"])
        self.assertEqual(analysis["primary"]["type"], "gradle-android")
        self.assertEqual(analysis["primary"]["commands"]["lint"], "./gradlew :app:lintDebug")
        self.assertEqual(analysis["primary"]["commands"]["test"], "./gradlew :app:testDebugUnitTest")
        self.assertEqual(analysis["primary"]["commands"]["build"], "./gradlew :app:assembleDebug")

    def test_build_ci_workflow_node(self):
        workflow = build_ci_workflow({
            "type": "node",
            "packageManager": "npm",
            "nodeVersion": {"source": "value", "value": "20"},
            "commands": {
                "install": "npm ci",
                "lint": "npm run lint",
                "test": "npm test",
                "build": "npm run build",
                "pack": "npm pack --dry-run"
            }
        })

        self.assertIn("actions/setup-node@v4", workflow)
        self.assertIn("run: npm ci", workflow)
        self.assertIn("run: npm run lint", workflow)
        self.assertIn("run: npm test", workflow)
        self.assertIn("run: npm run build", workflow)
        self.assertIn("run: npm pack --dry-run", workflow)

    def test_resolve_pipeline_selection(self):
        selection = resolve_pipeline_selection(
            {
                "options": [
                    {"id": "ci", "label": "CI"},
                    {"id": "ci-release", "label": "Release"}
                ]
            },
            "2"
        )

        self.assertEqual(selection, {"id": "ci-release", "label": "Release"})

    def test_write_pipeline_files(self):
        with open(os.path.join(self.cwd, "package.json"), "w", encoding="utf-8") as f:
            json.dump({
                "name": "demo-cli",
                "version": "1.0.0",
                "scripts": {
                    "test": "node --test"
                }
            }, f, indent=2)
        with open(os.path.join(self.cwd, "package-lock.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        analysis = inspect_repository_for_pipeline(self.cwd)
        selection = next(o for o in analysis["options"] if o["id"] == "ci-release")
        result = write_pipeline_files(self.cwd, analysis, selection)

        self.assertEqual(sorted(result["writtenFiles"]), [".github/workflows/ci.yml", ".github/workflows/release.yml"])
        self.assertEqual(sorted(result["updatedFiles"]), [".github/workflows/ci.yml", ".github/workflows/release.yml"])
        self.assertEqual(result["unchangedFiles"], [])

        with open(os.path.join(self.cwd, ".github/workflows/ci.yml"), "r", encoding="utf-8") as f:
            ci_content = f.read()
        
        self.assertIn("name: CI", ci_content)
        self.assertIn("run: npm test", ci_content)

if __name__ == "__main__":
    unittest.main()
