import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .git import run_git_command

WORKFLOW_DIR = ".github/workflows"

def file_exists(cwd: str, relative_path: str) -> bool:
    return Path(cwd).joinpath(relative_path).exists()

def detect_package_manager(cwd: str) -> str:
    if file_exists(cwd, "pnpm-lock.yaml"):
        return "pnpm"
    if file_exists(cwd, "yarn.lock"):
        return "yarn"
    if file_exists(cwd, "package-lock.json"):
        return "npm"
    return "npm"

def normalize_node_version(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    match = re.search(r'\d+(?:\.\d+){0,2}', raw.strip())
    return match.group(0) if match else None

def detect_node_version(cwd: str, package_json: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if file_exists(cwd, ".nvmrc"):
        return {
            "source": "file",
            "value": ".nvmrc"
        }

    engines_node = package_json.get("engines", {}).get("node") if package_json else None
    engine_version = normalize_node_version(engines_node)
    if engine_version:
        return {
            "source": "value",
            "value": engine_version
        }

    return {
        "source": "value",
        "value": "20"
    }

def detect_github_repository(cwd: str) -> Optional[Dict[str, str]]:
    try:
        remote = run_git_command(["config", "--get", "remote.origin.url"], cwd).strip()
        match = (
            re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote, re.IGNORECASE) or
            re.search(r'^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', remote, re.IGNORECASE)
        )
        if not match:
            return None
        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "slug": f"{match.group(1)}/{match.group(2)}"
        }
    except Exception:
        return None

def detect_node_packaging(cwd: str, package_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    package_name = (package_json.get("name", "package") if package_json else "package")
    package_name = re.sub(r'^@[^/]+/', '', package_name)
    github_repository = detect_github_repository(cwd)
    homebrew_formula_path = f"packaging/homebrew-tap/Formula/{package_name}.rb"

    return {
        "deb": file_exists(cwd, "scripts/build-deb.sh"),
        "aur": file_exists(cwd, "packaging/aur/PKGBUILD"),
        "homebrew": file_exists(cwd, homebrew_formula_path),
        "homebrewFormulaPath": homebrew_formula_path,
        "homebrewTapRepo": f"{github_repository['owner']}/homebrew-tap" if github_repository else None,
        "githubRepository": github_repository
    }

def to_homebrew_class_name(package_name: str) -> str:
    cleaned = re.sub(r'^@[^/]+/', '', package_name)
    parts = [part for part in re.split(r'[^a-zA-Z0-9]+', cleaned) if part]
    return "".join(part.capitalize() for part in parts)

def detect_node_project(cwd: str) -> Optional[Dict[str, Any]]:
    package_json_path = Path(cwd) / "package.json"
    if not package_json_path.exists():
        return None

    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            package_json = json.load(f)
    except Exception:
        package_json = {}

    scripts = package_json.get("scripts", {})
    node_version = detect_node_version(cwd, package_json)
    package_manager = detect_package_manager(cwd)
    release_supported = package_json.get("private") is not True and isinstance(package_json.get("name"), str)
    pack_supported = package_json.get("private") is not True or bool(package_json.get("bin"))
    packaging = detect_node_packaging(cwd, package_json)

    install_cmd = "npm ci"
    if package_manager == "pnpm":
        install_cmd = "pnpm install --frozen-lockfile"
    elif package_manager == "yarn":
        install_cmd = "yarn install --frozen-lockfile"

    return {
        "type": "node",
        "displayName": package_json.get("name") or Path(cwd).name,
        "packageManager": package_manager,
        "packageJson": package_json,
        "packaging": packaging,
        "nodeVersion": node_version,
        "commands": {
            "install": install_cmd,
            "lint": f"{package_manager} run lint" if isinstance(scripts.get("lint"), str) else None,
            "test": f"{package_manager} test" if isinstance(scripts.get("test"), str) else None,
            "build": f"{package_manager} run build" if isinstance(scripts.get("build"), str) else None,
            "pack": "npm pack --dry-run" if pack_supported else None
        },
        "release": {
            "supported": release_supported,
            "type": "npm",
            "packageName": package_json.get("name")
        }
    }

def detect_python_project(cwd: str) -> Optional[Dict[str, Any]]:
    if not file_exists(cwd, "pyproject.toml") and not file_exists(cwd, "requirements.txt"):
        return None

    install_cmd = "python -m pip install -e ."
    if file_exists(cwd, "requirements.txt"):
        install_cmd = "python -m pip install -r requirements.txt"

    test_cmd = None
    if file_exists(cwd, "pytest.ini") or file_exists(cwd, "tests"):
        test_cmd = "pytest"

    return {
        "type": "python",
        "displayName": Path(cwd).name,
        "commands": {
            "install": install_cmd,
            "lint": None,
            "test": test_cmd,
            "build": "python -m build",
            "pack": None
        },
        "release": {
            "supported": file_exists(cwd, "pyproject.toml"),
            "type": "pypi",
            "packageName": None
        }
    }

def detect_go_project(cwd: str) -> Optional[Dict[str, Any]]:
    if not file_exists(cwd, "go.mod"):
        return None

    return {
        "type": "go",
        "displayName": Path(cwd).name,
        "commands": {
            "install": "go mod download",
            "lint": None,
            "test": "go test ./...",
            "build": "go build ./...",
            "pack": None
        },
        "release": {
            "supported": False,
            "type": None,
            "packageName": None
        }
    }

def detect_rust_project(cwd: str) -> Optional[Dict[str, Any]]:
    if not file_exists(cwd, "Cargo.toml"):
        return None

    return {
        "type": "rust",
        "displayName": Path(cwd).name,
        "commands": {
            "install": "cargo fetch",
            "lint": "cargo fmt --check\ncargo clippy --all-targets --all-features -- -D warnings",
            "test": "cargo test --all-features",
            "build": "cargo build --release",
            "pack": None
        },
        "release": {
            "supported": True,
            "type": "crates",
            "packageName": None
        }
    }

def detect_gradle_project(cwd: str) -> Optional[Dict[str, Any]]:
    has_gradle_wrapper = file_exists(cwd, "gradlew")
    settings_files = ["settings.gradle.kts", "settings.gradle"]
    root_build_files = ["build.gradle.kts", "build.gradle"]
    app_build_files = [
        "app/build.gradle.kts",
        "app/build.gradle",
        "android/app/build.gradle.kts",
        "android/app/build.gradle"
    ]

    has_settings = any(file_exists(cwd, f) for f in settings_files)
    has_root_build = any(file_exists(cwd, f) for f in root_build_files)

    if not has_gradle_wrapper and not has_settings and not has_root_build:
        return None

    app_build_path = next((f for f in app_build_files if file_exists(cwd, f)), None)
    app_build_content = ""
    if app_build_path:
        try:
            with open(Path(cwd) / app_build_path, "r", encoding="utf-8") as f:
                app_build_content = f.read()
        except Exception:
            pass

    is_android_app = (
        "com.android.application" in app_build_content or
        "libs.plugins.android.application" in app_build_content or
        "android {" in app_build_content
    )

    gradle_command = "./gradlew" if has_gradle_wrapper else "gradle"
    display_name = Path(cwd).name

    if is_android_app:
        app_module = ":android:app" if app_build_path and app_build_path.startswith("android/") else ":app"
        return {
            "type": "gradle-android",
            "displayName": display_name,
            "commands": {
                "install": None,
                "lint": f"{gradle_command} {app_module}:lintDebug",
                "test": f"{gradle_command} {app_module}:testDebugUnitTest",
                "build": f"{gradle_command} {app_module}:assembleDebug",
                "pack": None
            },
            "release": {
                "supported": False,
                "type": None,
                "packageName": None
            }
        }

    return {
        "type": "gradle",
        "displayName": display_name,
        "commands": {
            "install": None,
            "lint": None,
            "test": f"{gradle_command} test",
            "build": f"{gradle_command} build",
            "pack": None
        },
        "release": {
            "supported": False,
            "type": None,
            "packageName": None
        }
    }

def detect_docker_support(cwd: str) -> bool:
    return file_exists(cwd, "Dockerfile")

def list_existing_workflows(cwd: str) -> List[str]:
    workflow_dir = Path(cwd) / WORKFLOW_DIR
    if not workflow_dir.exists():
        return []
    return [f.name for f in workflow_dir.glob("*") if f.suffix in (".yml", ".yaml")]

import json

def format_run_step(name: str, command: str, extra_lines: List[str] = None) -> str:
    if extra_lines is None:
        extra_lines = []

    lines = [f"      - name: {name}"]
    lines.extend(extra_lines)

    if "\n" in command:
        lines.append("        run: |")
        lines.extend(f"          {line}" for line in command.splitlines())
    else:
        lines.append(f"        run: {command}")

    return "\n".join(lines)

def build_node_setup_step(node_version: Dict[str, str], package_manager: str = "npm") -> str:
    if node_version.get("source") == "file":
        return (
            "      - name: Setup Node.js\n"
            "        uses: actions/setup-node@v4\n"
            "        with:\n"
            "          node-version-file: .nvmrc\n"
            f"          cache: {package_manager}\n"
            "          registry-url: 'https://registry.npmjs.org'\n"
            "          always-auth: true"
        )
    return (
        "      - name: Setup Node.js\n"
        "        uses: actions/setup-node@v4\n"
        "        with:\n"
        f"          node-version: '{node_version.get('value')}'\n"
        f"          cache: {package_manager}\n"
        "          registry-url: 'https://registry.npmjs.org'\n"
        "          always-auth: true"
    )

def build_install_step(context: Dict[str, Any]) -> str:
    ctype = context.get("type")
    commands = context.get("commands", {})

    if ctype == "node" and context.get("packageManager") in ("pnpm", "yarn"):
        return (
            "      - name: Enable Corepack\n"
            "        run: corepack enable\n"
            "      - name: Install dependencies\n"
            f"        run: {commands.get('install')}"
        )

    if ctype == "python":
        return (
            "      - name: Setup Python\n"
            "        uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: '3.12'\n"
            "      - name: Install dependencies\n"
            f"        run: {commands.get('install')}"
        )

    if ctype == "go":
        return (
            "      - name: Setup Go\n"
            "        uses: actions/setup-go@v5\n"
            "        with:\n"
            "          go-version: '1.22'\n"
            "      - name: Download modules\n"
            f"        run: {commands.get('install')}"
        )

    if ctype == "rust":
        return (
            "      - name: Install Rust toolchain\n"
            "        uses: dtolnay/rust-toolchain@stable\n" +
            format_run_step("Fetch dependencies", commands.get("install", ""))
        )

    if ctype in ("gradle", "gradle-android"):
        return (
            "      - name: Setup Java\n"
            "        uses: actions/setup-java@v4\n"
            "        with:\n"
            "          distribution: temurin\n"
            "          java-version: '17'\n"
            "      - name: Setup Gradle\n"
            "        uses: gradle/actions/setup-gradle@v4\n"
            "      - name: Make Gradle wrapper executable\n"
            "        run: chmod +x gradlew"
        )

    return format_run_step("Install dependencies", commands.get("install", ""))

def build_node_release_setup(context: Dict[str, Any]) -> str:
    lines = []
    lines.append(build_node_setup_step(context.get("nodeVersion", {}), context.get("packageManager", "npm")))

    if context.get("packageManager") in ("pnpm", "yarn"):
        lines.append("      - name: Enable Corepack\n        run: corepack enable")

    lines.append(format_run_step("Install dependencies", context.get("commands", {}).get("install", "")))
    return "\n".join(lines)

def build_run_steps(context: Dict[str, Any]) -> str:
    steps = []
    commands = context.get("commands", {})

    if commands.get("lint"):
        steps.append(format_run_step("Lint", commands["lint"]))
    if commands.get("test"):
        steps.append(format_run_step("Test", commands["test"]))
    if commands.get("build"):
        steps.append(format_run_step("Build", commands["build"]))
    if commands.get("pack"):
        extra = [
            "        env:",
            "          npm_config_cache: ${{ runner.temp }}/npm-cache"
        ] if context.get("type") == "node" else []
        steps.append(format_run_step("Verify package", commands["pack"], extra))

    return "\n".join(steps)

def inspect_repository_for_pipeline(cwd: str) -> Dict[str, Any]:
    node = detect_node_project(cwd)
    python = detect_python_project(cwd)
    go = detect_go_project(cwd)
    rust = detect_rust_project(cwd)
    gradle = detect_gradle_project(cwd)
    primary = node or python or go or rust or gradle

    if not primary:
        return {
            "supported": False,
            "reason": "No supported Node, Python, Go, Rust, or Gradle project files were detected.",
            "existingWorkflows": list_existing_workflows(cwd),
            "options": []
        }

    options = [
        {
            "id": "ci",
            "label": "GitHub Actions CI verification",
            "description": "Runs install, lint, test, build, and package checks when supported.",
            "files": [".github/workflows/ci.yml"]
        },
        {
            "id": "gitlab-ci",
            "label": "GitLab CI verification",
            "description": "Creates a .gitlab-ci.yml pipeline with install, lint, test, and build stages.",
            "files": [".gitlab-ci.yml"]
        },
        {
            "id": "circleci",
            "label": "CircleCI verification",
            "description": "Creates a .circleci/config.yml pipeline for verification jobs.",
            "files": [".circleci/config.yml"]
        },
        {
            "id": "bitbucket-pipelines",
            "label": "Bitbucket Pipelines verification",
            "description": "Creates bitbucket-pipelines.yml with install, test, and build steps.",
            "files": ["bitbucket-pipelines.yml"]
        }
    ]

    release_info = primary.get("release", {})
    if release_info.get("supported"):
        packaging = primary.get("packaging", {})
        if primary.get("type") == "node" and (packaging.get("deb") or packaging.get("homebrew") or packaging.get("aur")):
            desc = "Publishes to npm on version tags, builds Debian packages, updates Homebrew when configured, and prints AUR update instructions."
        elif primary.get("type") == "node":
            desc = "Publishes to npm when you push a version tag like v1.2.3."
        elif primary.get("type") == "python":
            desc = "Builds and publishes to PyPI when you push a version tag like v1.2.3."
        else:
            desc = "Publishes to crates.io when you push a version tag like v1.2.3."

        options.append({
            "id": "ci-release",
            "label": f"CI plus {release_info.get('type')} release automation",
            "description": desc,
            "files": [".github/workflows/ci.yml", ".github/workflows/release.yml"]
        })

    if detect_docker_support(cwd):
        options.append({
            "id": "container",
            "label": "Container build and GHCR publish",
            "description": "Builds the Docker image in CI and publishes it to GitHub Container Registry on tags.",
            "files": [".github/workflows/container.yml"]
        })

    return {
        "supported": True,
        "primary": primary,
        "existingWorkflows": list_existing_workflows(cwd),
        "options": options
    }

def format_pipeline_recommendations(analysis: Dict[str, Any]) -> str:
    if not analysis.get("supported"):
        return analysis.get("reason", "Not supported")

    primary = analysis["primary"]
    lines = [
        f"Detected project type: {primary.get('type')}",
        f"Project: {primary.get('displayName')}"
    ]

    commands = primary.get("commands", {})
    if primary.get("type") == "node":
        lines.append(f"Package manager: {primary.get('packageManager')}")

    for cmd_key in ["lint", "test", "build"]:
        if commands.get(cmd_key):
            lines.append(f"{cmd_key.capitalize()} command: {commands[cmd_key]}")

    existing = analysis.get("existingWorkflows", [])
    lines.append(f"Existing workflows: {', '.join(existing)}" if existing else "Existing workflows: none")
    lines.append("")
    lines.append("Available pipeline options:")

    for index, option in enumerate(analysis.get("options", [])):
        lines.append(f"{index + 1}. {option['label']}")
        lines.append(f"   {option['description']}")
        lines.append(f"   Files: {', '.join(option['files'])}")

    return "\n".join(lines)

def resolve_pipeline_selection(analysis: Dict[str, Any], response: str) -> Optional[Dict[str, Any]]:
    normalized = response.strip().lower()
    if normalized in ("cancel", "q", "quit"):
        return None

    try:
        numeric = int(normalized)
        options = analysis.get("options", [])
        if 1 <= numeric <= len(options):
            return options[numeric - 1]
    except ValueError:
        pass

    for option in analysis.get("options", []):
        if option["id"] == normalized:
            return option
    return None

def build_ci_workflow(context: Dict[str, Any]) -> str:
    lines = [
        "name: CI",
        "",
        "on:",
        "  push:",
        "    branches: [main, master]",
        "  pull_request:",
        "",
        "jobs:",
        "  verify:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - name: Checkout",
        "        uses: actions/checkout@v4"
    ]

    if context.get("type") == "node":
        lines.append(build_node_setup_step(context.get("nodeVersion", {}), context.get("packageManager", "npm")))

    lines.append(build_install_step(context))

    run_steps = build_run_steps(context)
    if run_steps:
        lines.append(run_steps)

    return "\n".join(lines) + "\n"

def build_release_workflow(context: Dict[str, Any]) -> str:
    release_info = context.get("release", {})
    if not release_info.get("supported"):
        raise ValueError(f"Release automation is not supported for {context.get('type')} repositories.")

    ctype = context.get("type")

    if ctype == "node":
        packaging = context.get("packaging", {})
        github_repository = packaging.get("githubRepository", {}).get("slug") if packaging.get("githubRepository") else None
        homebrew_tap_repo = packaging.get("homebrewTapRepo")
        package_json = context.get("packageJson", {})
        package_name = package_json.get("name") or context.get("displayName") or "package"
        formula_class_name = to_homebrew_class_name(package_name)
        bin_entries = list(package_json.get("bin", {}).items())
        executable_path = (bin_entries[0][1] if bin_entries else "cli/index.js").replace("./", "")
        executable_names = [name for name, _ in bin_entries] if bin_entries else [package_name]

        if packaging.get("deb") or packaging.get("homebrew") or packaging.get("aur"):
            lines = [
                "name: Release",
                "",
                "on:",
                "  push:",
                "    tags:",
                "      - 'v*'",
                "",
                "permissions:",
                "  contents: write",
                "",
                "jobs:",
                "  release:",
                "    if: startsWith(github.ref_name, 'v')",
                "    runs-on: ubuntu-latest",
                "",
                "    steps:",
                "      - name: Checkout",
                "        uses: actions/checkout@v4",
                build_node_release_setup(context),
                "      - name: Derive release metadata",
                "        id: meta",
                "        run: |",
                '          VERSION="${GITHUB_REF_NAME#v}"',
                '          echo "version=${VERSION}" >> "${GITHUB_OUTPUT}"'
            ]
            if packaging.get("deb"):
                lines.append(f'          echo "deb_path=dist/{package_name}_${{VERSION}}_all.deb" >> "${{GITHUB_OUTPUT}}"')

            commands = context.get("commands", {})
            if commands.get("test"):
                lines.append(format_run_step("Test", commands["test"]))
            if commands.get("build"):
                lines.append(format_run_step("Build", commands["build"]))
            if packaging.get("deb"):
                lines.append(format_run_step("Build Debian package", "./scripts/build-deb.sh"))

            lines.extend([
                "      - name: Verify npm token",
                "        env:",
                "          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}",
                "        run: |",
                '          if [ -z "${NODE_AUTH_TOKEN}" ]; then',
                '            echo "NPM_TOKEN is not configured for this repository."',
                '            echo "Add it in GitHub: Settings -> Secrets and variables -> Actions -> New repository secret."',
                "            exit 1",
                "          fi",
                '          printf "//registry.npmjs.org/:_authToken=%s\\n" "${NODE_AUTH_TOKEN}" > "${HOME}/.npmrc"',
                "          npm whoami",
                "      - name: Check whether npm version already exists",
                "        id: npm_version",
                "        run: |",
                '          VERSION="${{ steps.meta.outputs.version }}"',
                f'          if npm view "{package_name}@${{VERSION}}" version >/dev/null 2>&1; then',
                '            echo "published=true" >> "${GITHUB_OUTPUT}"',
                f'            echo "{package_name}@${{VERSION}} is already published on npm. Skipping npm publish."',
                "          else",
                '            echo "published=false" >> "${GITHUB_OUTPUT}"',
                "          fi",
                "      - name: Publish to npm",
                "        if: steps.npm_version.outputs.published != 'true'",
                "        env:",
                "          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}",
                "        run: npm publish",
                "      - name: Compute npm tarball SHA-256",
                "        id: npm",
                "        run: |",
                '          VERSION="${{ steps.meta.outputs.version }}"',
                f'          TARBALL_URL="https://registry.npmjs.org/{package_name}/-/{package_name}-${{VERSION}}.tgz"',
                "          for attempt in $(seq 1 24); do",
                '            if curl -fsSL "${TARBALL_URL}" -o ' + f'"{package_name}-${{VERSION}}.tgz"; then',
                "              break",
                "            fi",
                "",
                '            if [ "${attempt}" -eq 24 ]; then',
                '              echo "npm tarball was not available after waiting for registry propagation."',
                "              exit 1",
                "            fi",
                "",
                '            echo "Tarball not available yet. Waiting 5 seconds before retry ${attempt}/24..."',
                "            sleep 5",
                "          done",
                f'          SHA256="$(sha256sum "{package_name}-${{VERSION}}.tgz" | awk \'{{print $1}}\')"',
                '          echo "tarball_url=${TARBALL_URL}" >> "${GITHUB_OUTPUT}"',
                '          echo "sha256=${SHA256}" >> "${GITHUB_OUTPUT}"'
            ])

            if packaging.get("homebrew") and homebrew_tap_repo:
                homepage = f"https://github.com/{github_repository}" if github_repository else ""
                lines.extend([
                    "      - name: Checkout Homebrew tap",
                    "        uses: actions/checkout@v4",
                    "        with:",
                    f"          repository: {homebrew_tap_repo}",
                    "          token: ${{ secrets.HOMEBREW_TAP_TOKEN }}",
                    "          path: homebrew-tap",
                    "      - name: Update Homebrew formula",
                    "        run: |",
                    '          VERSION="${{ steps.meta.outputs.version }}"',
                    '          SHA256="${{ steps.npm.outputs.sha256 }}"',
                    f'          FORMULA_PATH="homebrew-tap/Formula/{package_name}.rb"',
                    '          mkdir -p "$(dirname "${FORMULA_PATH}")"',
                    '          cat > "${FORMULA_PATH}" <<EOF',
                    f'          class {formula_class_name} < Formula',
                    f'            desc {json.dumps(package_json.get("description", ""))}',
                    f'            homepage {json.dumps(homepage)}',
                    f'            url "https://registry.npmjs.org/{package_name}/-/{package_name}-' + '#{VERSION}.tgz"',
                    '            sha256 "${SHA256}"',
                    f'            license {json.dumps(package_json.get("license", "MIT"))}',
                    "",
                    '            depends_on "node"',
                    "",
                    "            def install",
                    '              libexec.install Dir["package/*"]',
                ])
                for name in executable_names:
                    lines.append(f'              bin.install_symlink libexec/"{executable_path}" => "{name}"')
                lines.extend([
                    "            end",
                    "",
                    "            test do",
                    f'              assert_match {json.dumps(executable_names[0])}, shell_output("#{{bin}}/{executable_names[0]} --help")',
                    "            end",
                    "          end",
                    "          EOF",
                    "      - name: Commit and push Homebrew tap changes",
                    "        working-directory: homebrew-tap",
                    "        run: |",
                    '          git config user.name "github-actions[bot]"',
                    '          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"',
                    f'          git add Formula/{package_name}.rb',
                    "          if git diff --cached --quiet; then",
                    '            echo "No Homebrew formula changes to commit."',
                    "            exit 0",
                    "          fi",
                    '          git commit -m "gx ${GITHUB_REF_NAME}"',
                    "          git push"
                ])

            if packaging.get("deb"):
                lines.extend([
                    "      - name: Create GitHub release and upload Debian package",
                    "        uses: softprops/action-gh-release@v2",
                    "        with:",
                    "          files: ${{ steps.meta.outputs.deb_path }}"
                ])

            if packaging.get("aur"):
                lines.extend([
                    "      - name: Print AUR update instructions",
                    "        run: |",
                    '          VERSION="${{ steps.meta.outputs.version }}"',
                    '          SHA256="${{ steps.npm.outputs.sha256 }}"',
                    '          echo "Manual AUR update steps:"',
                    '          echo "1. Update packaging/aur/PKGBUILD with pkgver=${VERSION} and sha256sums=(\'${SHA256}\')."',
                    '          echo "2. Run: makepkg --printsrcinfo > .SRCINFO"',
                    '          echo "3. Commit PKGBUILD and .SRCINFO to the AUR git repository and push."'
                ])

            return "\n".join(lines) + "\n"

        # Regular Node project release (no native OS packaging)
        return "\n".join([
            "name: Release",
            "",
            "on:",
            "  push:",
            "    tags:",
            "      - 'v*'",
            "",
            "jobs:",
            "  publish:",
            "    if: startsWith(github.ref_name, 'v')",
            "    runs-on: ubuntu-latest",
            "    permissions:",
            "      contents: read",
            "    steps:",
            "      - name: Checkout",
            "        uses: actions/checkout@v4",
            build_node_release_setup(context),
        ] + (
            [format_run_step("Test", context["commands"]["test"])] if context.get("commands", {}).get("test") else []
        ) + (
            [format_run_step("Build", context["commands"]["build"])] if context.get("commands", {}).get("build") else []
        ) + [
            "      - name: Verify npm token",
            "        env:",
            "          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}",
            "        run: |",
            '          if [ -z "${NODE_AUTH_TOKEN}" ]; then',
            '            echo "NPM_TOKEN is not configured for this repository."',
            '            echo "Add it in GitHub: Settings -> Secrets and variables -> Actions -> New repository secret."',
            "            exit 1",
            "          fi",
            '          printf "//registry.npmjs.org/:_authToken=%s\\n" "${NODE_AUTH_TOKEN}" > "${HOME}/.npmrc"',
            "          npm whoami",
            "      - name: Check whether npm version already exists",
            "        id: npm_version",
            "        run: |",
            '          VERSION="${{ steps.meta.outputs.version }}"',
            f'          if npm view "{package_name}@${{VERSION}}" version >/dev/null 2>&1; then',
            '            echo "published=true" >> "${GITHUB_OUTPUT}"',
            f'            echo "{package_name}@${{VERSION}} is already published on npm. Skipping npm publish."',
            "          else",
            '            echo "published=false" >> "${GITHUB_OUTPUT}"',
            "          fi",
            "      - name: Publish to npm",
            "        if: steps.npm_version.outputs.published != 'true'",
            "        env:",
            "          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}",
            "        run: npm publish"
        ]) + "\n"

    if ctype == "python":
        return "\n".join([
            "name: Release",
            "",
            "on:",
            "  push:",
            "    tags:",
            "      - 'v*'",
            "",
            "jobs:",
            "  publish:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - name: Checkout",
            "        uses: actions/checkout@v4",
            "      - name: Setup Python",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: '3.12'",
            "      - name: Install build tools",
            "        run: python -m pip install build twine",
            "      - name: Build package",
            "        run: python -m build",
            "      - name: Publish to PyPI",
            "        env:",
            "          TWINE_USERNAME: __token__",
            "          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}",
            "        run: python -m twine upload dist/*"
        ]) + "\n"

    # Default: crates.io (Rust)
    return "\n".join([
        "name: Release",
        "",
        "on:",
        "  push:",
        "    tags:",
        "      - 'v*'",
        "",
        "jobs:",
        "  publish:",
        "    if: startsWith(github.ref_name, 'v')",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - name: Checkout",
        "        uses: actions/checkout@v4",
        "      - name: Install Rust toolchain",
        "        uses: dtolnay/rust-toolchain@stable",
        "      - name: Publish to crates.io",
        "        env:",
        "          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}",
        "        run: cargo publish --locked"
    ]) + "\n"

def build_container_workflow() -> str:
    return "\n".join([
        "name: Container",
        "",
        "on:",
        "  push:",
        "    branches: [main, master]",
        "    tags:",
        "      - 'v*'",
        "  pull_request:",
        "",
        "jobs:",
        "  docker:",
        "    runs-on: ubuntu-latest",
        "    permissions:",
        "      contents: read",
        "      packages: write",
        "    steps:",
        "      - name: Checkout",
        "        uses: actions/checkout@v4",
        "      - name: Log in to GHCR",
        "        if: github.event_name != 'pull_request'",
        "        uses: docker/login-action@v3",
        "        with:",
        "          registry: ghcr.io",
        "          username: ${{ github.actor }}",
        "          password: ${{ secrets.GITHUB_TOKEN }}",
        "      - name: Extract metadata",
        "        id: meta",
        "        uses: docker/metadata-action@v5",
        "        with:",
        "          images: ghcr.io/${{ github.repository }}",
        "      - name: Build and push image",
        "        uses: docker/build-push-action@v6",
        "        with:",
        "          context: .",
        "          push: ${{ github.event_name != 'pull_request' }}",
        "          tags: ${{ steps.meta.outputs.tags }}",
        "          labels: ${{ steps.meta.outputs.labels }}"
    ]) + "\n"

def build_pipeline_commands(context: Dict[str, Any]) -> List[str]:
    commands = context.get("commands", {})
    return [
        commands.get(k) for k in ["install", "lint", "test", "build", "pack"] if commands.get(k)
    ]

def build_gitlab_ci_workflow(context: Dict[str, Any]) -> str:
    commands = build_pipeline_commands(context)
    ctype = context.get("type")

    image = "node:20"
    if ctype == "python":
        image = "python:3.12"
    elif ctype == "go":
        image = "golang:1.22"
    elif ctype == "rust":
        image = "rust:latest"

    lines = [
        f"image: {image}",
        "",
        "stages:",
        "  - verify",
        "",
        "verify:",
        "  stage: verify",
        "  script:"
    ]
    lines.extend(f"    - {cmd}" for cmd in commands)
    return "\n".join(lines) + "\n"

def build_circle_ci_workflow(context: Dict[str, Any]) -> str:
    ctype = context.get("type")
    image = "cimg/node:20.10"
    if ctype == "python":
        image = "cimg/python:3.12"
    elif ctype == "go":
        image = "cimg/go:1.22"
    elif ctype == "rust":
        image = "cimg/rust:1.83"

    commands = build_pipeline_commands(context)
    lines = [
        "version: 2.1",
        "",
        "jobs:",
        "  verify:",
        "    docker:",
        f"      - image: {image}",
        "    steps:",
        "      - checkout"
    ]
    lines.extend(f"      - run: {cmd}" for cmd in commands)
    lines.extend([
        "",
        "workflows:",
        "  verify:",
        "    jobs:",
        "      - verify"
    ])
    return "\n".join(lines) + "\n"

def build_bitbucket_pipelines_workflow(context: Dict[str, Any]) -> str:
    ctype = context.get("type")
    image = "node:20"
    if ctype == "python":
        image = "python:3.12"
    elif ctype == "go":
        image = "golang:1.22"
    elif ctype == "rust":
        image = "rust:latest"

    commands = build_pipeline_commands(context)
    lines = [
        f"image: {image}",
        "",
        "pipelines:",
        "  default:",
        "    - step:",
        "        name: Verify",
        "        script:"
    ]
    lines.extend(f"          - {cmd}" for cmd in commands)
    return "\n".join(lines) + "\n"

def write_pipeline_files(cwd: str, analysis: Dict[str, Any], selection: Dict[str, Any]) -> Dict[str, Any]:
    if not analysis.get("supported"):
        raise ValueError(analysis.get("reason", "Not supported"))

    written_files = []
    updated_files = []
    unchanged_files = []
    notes = []

    def write_workflow(relative_path: str, contents: str) -> None:
        abs_path = Path(cwd) / relative_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing_contents = None
        if abs_path.exists():
            with open(abs_path, "r", encoding="utf-8") as f:
                existing_contents = f.read()

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(contents)

        written_files.append(relative_path)
        if existing_contents == contents:
            unchanged_files.append(relative_path)
        else:
            updated_files.append(relative_path)

    sid = selection.get("id")
    primary = analysis.get("primary", {})

    if sid in ("ci", "ci-release"):
        write_workflow(".github/workflows/ci.yml", build_ci_workflow(primary))

    if sid == "ci-release":
        write_workflow(".github/workflows/release.yml", build_release_workflow(primary))

        rtype = primary.get("release", {}).get("type")
        if rtype == "npm":
            notes.append("Add an `NPM_TOKEN` repository secret before pushing a release tag.")
            packaging = primary.get("packaging", {})
            if packaging.get("homebrew"):
                notes.append("Add a `HOMEBREW_TAP_TOKEN` repository secret so CI can update your tap repository.")
            if packaging.get("aur"):
                notes.append("AUR updates are still manual. The generated release workflow prints the exact PKGBUILD and .SRCINFO refresh steps.")
        elif rtype == "pypi":
            notes.append("Add a `PYPI_TOKEN` repository secret before pushing a release tag.")
        elif rtype == "crates":
            notes.append("Add a `CARGO_REGISTRY_TOKEN` repository secret before pushing a release tag.")

    if sid == "container":
        write_workflow(".github/workflows/container.yml", build_container_workflow())

    if sid == "gitlab-ci":
        write_workflow(".gitlab-ci.yml", build_gitlab_ci_workflow(primary))

    if sid == "circleci":
        write_workflow(".circleci/config.yml", build_circle_ci_workflow(primary))

    if sid == "bitbucket-pipelines":
        write_workflow("bitbucket-pipelines.yml", build_bitbucket_pipelines_workflow(primary))

    if sid == "container" and ".github/workflows/ci.yml" not in selection.get("files", []):
        notes.append("This option only creates the container workflow. Run `gx --pipeline` again if you also want CI verification.")

    return {
        "writtenFiles": written_files,
        "updatedFiles": updated_files,
        "unchangedFiles": unchanged_files,
        "notes": notes
    }
