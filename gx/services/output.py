import html
import json
import re
from typing import Any, Dict, List, Optional
from .color import ANSI, colorize

def strip_inline_markdown(text: str) -> str:
    # Strip backticks, bold/italic markers, and links
    res = text
    res = re.sub(r'`([^`]+)`', r'\1', res)
    res = re.sub(r'\*\*([^*]+)\*\*|__([^_]+)__', r'\1\2', res)
    res = re.sub(r'\*([^*]+)\*|_([^_]+)_', r'\1\2', res)
    res = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', res)
    return res.rstrip()

class MarkdownState:
    def __init__(self):
        self.inCodeBlock = False

def normalize_markdown_line(line: str, state: MarkdownState) -> str:
    trimmed = line.strip()

    if trimmed.startswith("```"):
        state.inCodeBlock = not state.inCodeBlock
        return ""

    if state.inCodeBlock:
        return "  " + line.lstrip()

    if re.match(r'^---+$|^\*\*\*+$', trimmed):
        return ""

    normalized_heading = re.sub(r'^#{1,6}\s+', '', trimmed)
    normalized_heading = re.sub(r'^([0-9]+\.)\s+', '', normalized_heading)
    normalized_heading = strip_inline_markdown(normalized_heading)
    normalized_heading = re.sub(r':\s*$', '', normalized_heading).strip()

    header_pattern = (
        r'^(summary|issues? fixed|issue|root cause|fix(?: explanation)?|impact|'
        r'risk level|severity|technical breakdown|full analysis|'
        r'line-by-line code walkthrough|code review|security review|'
        r'security findings|review findings|suggestions|recommended mitigations)$'
    )
    if re.match(header_pattern, normalized_heading, re.IGNORECASE):
        return f"{normalized_heading}:"

    if trimmed.startswith(">"):
        return strip_inline_markdown(trimmed[1:].lstrip())

    bullet_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.*)$', line)
    if bullet_match:
        indent, marker, content = bullet_match.groups()
        return f"{indent}{marker} {strip_inline_markdown(content)}"

    return strip_inline_markdown(line)

def format_target_label(commit_data: Dict[str, Any]) -> str:
    analysis_type = commit_data.get("analysisType")
    if analysis_type == "range":
        return "Range"
    if analysis_type == "blame":
        return "File"
    if analysis_type == "stash":
        return "Stash"
    if analysis_type == "conflict":
        return "Conflict"
    return "Commit"

def normalize_heading(line: str) -> Optional[str]:
    match = re.match(
        r'^([0-9]+\.)?\s*(Summary|Issues? Fixed|Issue|Root Cause|Fix(?: Explanation)?|Impact|'
        r'Risk Level|Severity|Technical Breakdown|Full Analysis|Line-by-Line Code Walkthrough|'
        r'Code Review|Security Review|Security Findings|Review Findings|Suggestions|'
        r'Recommended Mitigations)\s*:?\s*$',
        line,
        re.IGNORECASE
    )
    if not match:
        return None
    return f"{match.group(2)}:"

def is_file_heading(line: str) -> bool:
    return bool(
        re.match(r'^(?:File|Path)\s*:', line, re.IGNORECASE) or
        re.match(r'^[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:\s*$', line)
    )

def format_bullet_line(line: str) -> Optional[str]:
    match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', line)
    if not match:
        return None
    indent, marker, content = match.groups()
    return f"{indent}{colorize(marker, ANSI.cyan)} {content}"

def format_severity_line(line: str) -> Optional[str]:
    if not re.search(r'\brisk level\b|\bseverity\b', line, re.IGNORECASE):
        return None
    return line

def format_line(line: str) -> str:
    trimmed = line.strip()
    if trimmed == "":
        return ""

    normalized = normalize_heading(trimmed)
    if normalized:
        return colorize(normalized, ANSI.bold + ANSI.cyan)

    if is_file_heading(trimmed):
        return colorize(trimmed, ANSI.bold + ANSI.cyan)

    bullet = format_bullet_line(line)
    if bullet:
        return bullet

    severity = format_severity_line(trimmed)
    if severity:
        return severity

    return line

def format_explanation(explanation: str) -> str:
    state = MarkdownState()
    normalized_lines = []
    
    # Standardize newlines
    raw_lines = explanation.replace("\r\n", "\n").split("\n")
    for line in raw_lines:
        normalized_lines.append(normalize_markdown_line(line, state))

    formatted = []
    previous_was_blank = False

    for line in normalized_lines:
        trimmed = line.strip()
        formatted_line = format_line(line)
        is_heading = (normalize_heading(trimmed) is not None) or is_file_heading(trimmed)

        if trimmed == "":
            if not previous_was_blank and len(formatted) > 0:
                formatted.append("")
            previous_was_blank = True
            continue

        if is_heading and len(formatted) > 0 and not previous_was_blank:
            formatted.append("")

        formatted.append(formatted_line)
        previous_was_blank = False

    return "\n".join(formatted).rstrip()

def format_preamble(params: Dict[str, Any]) -> str:
    mode = params.get("mode")
    commit_data = params.get("commitData", {})
    options = params.get("options", {})
    prompt_meta = params.get("promptMeta", {})

    if options.get("quiet"):
        return ""

    header = [
        f"{colorize(format_target_label(commit_data), ANSI.bold + ANSI.cyan)}: {commit_data.get('displayRef')}",
        f"Files Changed: {len(commit_data.get('filesChanged', []))}",
        f"Stats: {commit_data.get('stats')}",
        f"Mode: {mode}"
    ]

    if commit_data.get("analysisType") == "range":
        header.insert(1, f"Commits: {commit_data.get('commitCount')}")

    if prompt_meta and prompt_meta.get("warnings"):
        for warning in prompt_meta["warnings"]:
            header.append(colorize(f"Warning: {warning}", ANSI.yellow))

    return "\n".join(header) + "\n\n"

def format_footer(params: Dict[str, Any]) -> str:
    response_meta = params.get("responseMeta")
    prompt_meta = params.get("promptMeta")
    options = params.get("options", {})

    if not options.get("verbose") or not response_meta:
        return ""

    lines = [
        "",
        colorize("Meta:", ANSI.bold + ANSI.gray),
        f"Provider: {response_meta.get('provider')}",
        f"Model: {response_meta.get('model')}",
        f"Cache: {'hit' if response_meta.get('cacheHit') else 'miss'}",
        f"Latency: {response_meta.get('latencyMs')}ms"
    ]

    if response_meta.get("usage"):
        lines.append(f"Usage: {json.dumps(response_meta['usage'])}")

    if response_meta.get("estimatedCostUsd") is not None:
        lines.append(f"Estimated Cost: ${response_meta['estimatedCostUsd']:.6f}")

    if prompt_meta and prompt_meta.get("warnings"):
        lines.extend(prompt_meta["warnings"])

    return "\n".join(lines) + "\n"

def format_output(params: Dict[str, Any]) -> str:
    return (
        format_preamble(params) +
        format_explanation(params.get("explanation", "")) +
        format_footer(params)
    )

def format_markdown_output(params: Dict[str, Any]) -> str:
    mode = params.get("mode")
    commit_data = params.get("commitData", {})
    explanation = params.get("explanation", "")
    response_meta = params.get("responseMeta", {})
    prompt_meta = params.get("promptMeta", {})

    lines = [
        "# gx",
        "",
        f"- Target: {commit_data.get('displayRef')}",
        f"- Type: {commit_data.get('analysisType')}",
        f"- Files Changed: {len(commit_data.get('filesChanged', []))}",
        f"- Stats: {commit_data.get('stats')}",
        f"- Mode: {mode}"
    ]

    if commit_data.get("analysisType") == "range":
        lines.append(f"- Commits: {commit_data.get('commitCount')}")

    if response_meta:
        lines.append(f"- Provider: {response_meta.get('provider')}")
        lines.append(f"- Model: {response_meta.get('model')}")

    if prompt_meta and prompt_meta.get("warnings"):
        for warning in prompt_meta["warnings"]:
            lines.append(f"- Warning: {warning}")

    lines.append("")
    lines.append(explanation)
    return "\n".join(lines)

def format_html_output(params: Dict[str, Any]) -> str:
    mode = params.get("mode")
    commit_data = params.get("commitData", {})
    explanation = params.get("explanation", "")
    response_meta = params.get("responseMeta", {})
    prompt_meta = params.get("promptMeta", {})

    meta_items = [
        f"<li><strong>Target:</strong> {html.escape(str(commit_data.get('displayRef')))}</li>",
        f"<li><strong>Type:</strong> {html.escape(str(commit_data.get('analysisType')))}</li>",
        f"<li><strong>Files Changed:</strong> {len(commit_data.get('filesChanged', []))}</li>",
        f"<li><strong>Stats:</strong> {html.escape(str(commit_data.get('stats')))}</li>",
        f"<li><strong>Mode:</strong> {html.escape(str(mode))}</li>"
    ]

    if commit_data.get("analysisType") == "range":
        meta_items.append(f"<li><strong>Commits:</strong> {commit_data.get('commitCount')}</li>")

    if response_meta:
        meta_items.append(f"<li><strong>Provider:</strong> {html.escape(str(response_meta.get('provider')))}</li>")
        meta_items.append(f"<li><strong>Model:</strong> {html.escape(str(response_meta.get('model')))}</li>")

    if prompt_meta and prompt_meta.get("warnings"):
        for warning in prompt_meta["warnings"]:
            meta_items.append(f"<li><strong>Warning:</strong> {html.escape(warning)}</li>")

    return "".join([
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>gx</title></head><body>",
        "<h1>gx</h1>",
        f"<ul>{''.join(meta_items)}</ul>",
        f"<pre>{html.escape(explanation)}</pre>",
        "</body></html>"
    ])

def format_json_output(params: Dict[str, Any]) -> str:
    commit_data = params.get("commitData", {})
    return json.dumps(
        {
            "mode": params.get("mode"),
            "commit": {
                "id": commit_data.get("commitId"),
                "ref": commit_data.get("displayRef"),
                "type": commit_data.get("analysisType"),
                "count": commit_data.get("commitCount"),
                "message": commit_data.get("commitMessage"),
                "filesChanged": commit_data.get("filesChanged"),
                "stats": commit_data.get("stats")
            },
            "prompt": params.get("promptMeta"),
            "response": params.get("responseMeta"),
            "explanation": params.get("explanation")
        },
        indent=2
    )
