#!/usr/bin/env python3
"""Проверка адаптеров без железа: python tests/test_adapters.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))

from adapters import ADAPTERS           # noqa: E402
from adapters.common import IDLE        # noqa: E402


def run(agent, events):
    state, ctx = dict(IDLE), {}
    history = []
    for ev in events:
        if ADAPTERS[agent].handle(ev, state, ctx):
            history.append(dict(state))
    return history


class ClaudeAdapter(unittest.TestCase):
    def test_full_task(self):
        h = run("claude", [
            {"hook_event_name": "UserPromptSubmit", "prompt": "Сделай   рефакторинг\nмодуля"},
            {"hook_event_name": "PreToolUse", "tool_name": "Edit",
             "tool_input": {"file_path": "/a/b/auth.ts"}},
            {"hook_event_name": "PostToolUse", "tool_name": "TodoWrite", "tool_input": {"todos": [
                {"content": "a", "activeForm": "Делаю a", "status": "completed"},
                {"content": "b", "activeForm": "Делаю b", "status": "in_progress"},
                {"content": "c", "status": "pending"}]}},
            {"hook_event_name": "Notification", "message": "Claude needs your permission"},
            {"hook_event_name": "Stop"},
        ])
        self.assertEqual(h[0]["state"], "start")
        self.assertEqual(h[0]["title"], "Сделай рефакторинг модуля")
        self.assertEqual(h[1]["step"], "Правит auth.ts")
        self.assertEqual((h[2]["done"], h[2]["total"], h[2]["step"]), (1, 3, "Делаю b"))
        self.assertEqual(h[3]["state"], "wait")
        self.assertEqual((h[4]["state"], h[4]["done"]), ("done", 3))

    def test_unknown_event_ignored(self):
        self.assertEqual(run("claude", [{"hook_event_name": "PreCompact"}]), [])


class CodexAdapter(unittest.TestCase):
    def test_full_task(self):
        h = run("codex", [
            {"hook_event_name": "UserPromptSubmit", "prompt": "Почини тесты"},
            {"hook_event_name": "PreToolUse", "tool_name": "shell",
             "tool_input": {"command": ["npm", "test"]}},
            {"hook_event_name": "PostToolUse", "tool_name": "update_plan", "tool_input": {"plan": [
                {"step": "Найти падающий тест", "status": "completed"},
                {"step": "Исправить код", "status": "in_progress"}]}},
            {"hook_event_name": "PermissionRequest", "tool_name": "shell",
             "tool_input": {"command": "rm -rf build"}},
            {"hook_event_name": "Stop"},
        ])
        self.assertEqual(h[0]["state"], "start")
        self.assertEqual(h[1]["step"], "$ npm test")
        self.assertEqual((h[2]["done"], h[2]["total"], h[2]["step"]), (1, 2, "Исправить код"))
        self.assertEqual(h[3]["state"], "wait")
        self.assertIn("rm -rf build", h[3]["step"])
        self.assertEqual((h[4]["state"], h[4]["done"]), ("done", 2))


class IdleScenes(unittest.TestCase):
    def test_defaults(self):
        from scenes import idle_scene
        self.assertEqual(idle_scene("claude", {}), "robot")
        self.assertEqual(idle_scene("codex", {}), "cursor")

    def test_env_choice_and_fallback(self):
        from scenes import idle_scene
        self.assertEqual(idle_scene("claude", {"AGENT_STATUS_IDLE_CLAUDE": "Cursor"}), "cursor")
        self.assertEqual(idle_scene("codex", {"AGENT_STATUS_IDLE_CODEX": "typist"}), "typist")
        self.assertEqual(idle_scene("codex", {"AGENT_STATUS_IDLE_CODEX": "robot"}), "cursor")
        self.assertIsNone(idle_scene("unknown", {}))


if __name__ == "__main__":
    unittest.main()
