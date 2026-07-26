"""
Smart Transit & Commuter Agent Skills Manager.

Loads ~/.smart_transit_agent/SKILL.md and ~/.smart_transit_agent/GOALS.md on TUI startup,
creating them from built-in templates if they don't exist yet.

The merged content is injected as the system prompt into run_agent(),
giving the agent a persistent identity, tool awareness, and active goal.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .config import CONFIG_DIR

# ── File paths ────────────────────────────────────────────────────────────────

SKILL_FILE = CONFIG_DIR / "SKILL.md"

def get_goals_file() -> Path:
    from .config import Config, SESSION_DIR
    cfg = Config.load()
    if cfg.active_session:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        return SESSION_DIR / f"{cfg.active_session}_GOALS.md"
    return CONFIG_DIR / "GOALS.md"

# ── Default templates ─────────────────────────────────────────────────────────

SKILL_TEMPLATE = """\
# Gemma Smart Commuter Agent

## Role
You are a Smart Commuter Agent, a local privacy-first AI agent powered by Gemma. 
Your primary goal is to help university students and commuters in Bangladesh (e.g. Dhaka) dynamically and autonomously plan the safest, most efficient routes around severe city traffic jams while predicting accurate travel times.

CRITICAL INSTRUCTION: You MUST communicate with the user entirely in Bengali. All conversational responses, reasoning, and summaries must be written in fluent Bengali. If tools return English data, translate the findings into Bengali for the user.

CRITICAL WORKFLOW:
1. You MUST ALWAYS create tasks using the `tasks_add` tool for every single user request before taking any other action. Write the task descriptions in Bengali.
2. When asked about a route or traffic, use the transit tools (`get_route_options`, `get_live_traffic`, `get_ride_estimate`) to execute your tasks and gather facts.
3. As soon as you finish a task, you MUST use the `tasks_done` tool to mark it complete. You MUST do this before responding to the user!
4. Synthesize the data into a clear, concise recommendation for the user in Bengali.

## Available Tools
- get_route_options            — find routes between origin and destination
- get_live_traffic             — check congestion at a specific location
- get_ride_estimate            — get ride-share price and ETA
- tasks_add, tasks_done        — track tasks silently
"""

GOALS_TEMPLATE = """\
# Goals

## Active Goal
(none — use /goal set <description> to define a goal)

## Completed Goals
(none yet)
"""


# ── SkillsManager ─────────────────────────────────────────────────────────────

class SkillsManager:
    """
    Loads SKILL.md and GOALS.md, creates them from templates if absent,
    and builds the enriched system prompt injected into run_agent().
    """

    def __init__(self) -> None:
        self.skill_content: str = SKILL_TEMPLATE
        self.goals_content: str = GOALS_TEMPLATE

    # ── Loading ───────────────────────────────────────────────────────────

    def load(self) -> None:
        """Read ~/.smart_transit_agent/SKILL.md and GOALS.md. Create from template if absent."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not SKILL_FILE.exists():
            SKILL_FILE.write_text(SKILL_TEMPLATE)
        goals_file = get_goals_file()
        if not goals_file.exists():
            goals_file.write_text(GOALS_TEMPLATE)
        self.skill_content = SKILL_FILE.read_text(errors="replace")
        self.goals_content = goals_file.read_text(errors="replace")

    def reload(self) -> None:
        """Re-read files from disk (e.g. after /goal set)."""
        self.load()

    # ── System prompt ─────────────────────────────────────────────────────

    def build_system_prompt(self) -> str:
        """Return the merged system prompt (SKILL.md + GOALS.md)."""
        prompt = (
            self.skill_content.strip()
            + "\n\n---\n\n"
            + self.goals_content.strip()
        )
        if self.active_goal:
            prompt += (
                f"\n\nYour overarching active goal is: '{self.active_goal}'\n"
                "You must use the `tasks_add` and `tasks_done` tools to manage your progress toward this goal."
            )
        return prompt

    # ── Goal management ───────────────────────────────────────────────────

    @property
    def active_goal(self) -> str:
        """Extract the active goal text from goals_content."""
        m = re.search(r"## Active Goal\n(.*?)(?=\n## |\Z)", self.goals_content, re.DOTALL)
        if m:
            text = m.group(1).strip()
            return text if not text.startswith("(none") else ""
        return ""

    def set_active_goal(self, goal: str) -> None:
        """Replace the Active Goal section in GOALS.md and save."""
        goals_file = get_goals_file()
        content = (
            goals_file.read_text(errors="replace")
            if goals_file.exists()
            else GOALS_TEMPLATE
        )
        new_section = f"## Active Goal\n{goal}\n"
        if re.search(r"^## Active Goal", content, re.MULTILINE):
            content = re.sub(
                r"## Active Goal\n.*?(?=\n## |\Z)",
                new_section,
                content,
                flags=re.DOTALL,
            )
        else:
            content += f"\n{new_section}"
        goals_file = get_goals_file()
        goals_file.write_text(content)
        self.goals_content = content

    def archive_active_goal(self) -> str:
        """Move Active Goal → Completed Goals. Returns the archived text."""
        content = (
            GOALS_FILE.read_text(errors="replace")
            if GOALS_FILE.exists()
            else GOALS_TEMPLATE
        )
        m = re.search(r"## Active Goal\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if not m:
            return ""
        active_text = m.group(1).strip()
        if not active_text or active_text.startswith("(none"):
            return ""

        date_str = datetime.now().strftime("%Y-%m-%d")
        content  = re.sub(
            r"## Active Goal\n.*?(?=\n## |\Z)",
            "## Active Goal\n(none — use /goal set <description> to define a goal)\n",
            content,
            flags=re.DOTALL,
        )
        entry = f"- [{date_str}] {active_text}\n"
        if "## Completed Goals" in content:
            if "(none yet)" in content:
                content = content.replace("(none yet)\n", entry)
            else:
                content = content.replace(
                    "## Completed Goals\n",
                    f"## Completed Goals\n{entry}",
                )
        else:
            content += f"\n## Completed Goals\n{entry}"

        goals_file = get_goals_file()
        goals_file.write_text(content)
        self.goals_content = content
        return active_text


# ── Global singleton ──────────────────────────────────────────────────────────

skills_manager = SkillsManager()
