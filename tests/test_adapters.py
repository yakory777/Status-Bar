#!/usr/bin/env python3
"""Проверка адаптеров без железа: python tests/test_adapters.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))

import config                           # noqa: E402
import i18n                             # noqa: E402
from adapters import ADAPTERS           # noqa: E402
from adapters.common import IDLE        # noqa: E402

i18n.set_language("ru")                 # тексты в проверках ниже — русские
NO_FILE = dict(read_file=False)         # не читать настоящий ~/.agent-status/config.toml


def settings(**env):
    return config.load(env=env, **NO_FILE)


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
        self.assertEqual(run("claude", [{"hook_event_name": "CwdChanged"}]), [])


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


class ClaudeScenarios(unittest.TestCase):
    def test_task_events_build_plan(self):
        h = run("claude", [
            {"hook_event_name": "UserPromptSubmit", "prompt": "Сделай фичу"},
            {"hook_event_name": "TaskCreated", "task_id": "1", "task_subject": "Найти место"},
            {"hook_event_name": "TaskCreated", "task_id": "2", "task_subject": "Написать код"},
            {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate",
             "tool_input": {"taskId": "1", "status": "in_progress", "activeForm": "Ищу место"}},
            {"hook_event_name": "TaskCompleted", "task_id": "1", "task_subject": "Найти место"},
        ])
        self.assertEqual((h[2]["done"], h[2]["total"]), (0, 2))
        self.assertEqual(h[3]["step"], "Ищу место")
        self.assertEqual((h[4]["done"], h[4]["total"]), (1, 2))

    def test_new_prompt_clears_finished_plan(self):
        h = run("claude", [
            {"hook_event_name": "TaskCreated", "task_id": "1", "task_subject": "a"},
            {"hook_event_name": "TaskCompleted", "task_id": "1"},
            {"hook_event_name": "UserPromptSubmit", "prompt": "Следующая"},
        ])
        self.assertEqual((h[-1]["done"], h[-1]["total"]), (0, 1))

    def test_tool_failure_then_recovery(self):
        h = run("claude", [
            {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
             "tool_input": {"command": "npm test"}, "error": "exit 1"},
            {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": "a.ts"}},
        ])
        self.assertEqual(h[0]["state"], "error")
        self.assertIn("npm test", h[0]["step"])
        self.assertEqual(h[1]["state"], "work")

    def test_stop_failure_reason(self):
        h = run("claude", [{"hook_event_name": "StopFailure", "error_type": "rate_limit"}])
        self.assertEqual(h[0]["state"], "error")
        self.assertIn("Лимит", h[0]["step"])

    def test_notification_types(self):
        h = run("claude", [
            {"hook_event_name": "Notification", "notification_type": "idle_prompt", "message": "x"},
            {"hook_event_name": "Notification", "notification_type": "permission_prompt",
             "message": "Claude needs your permission to use Bash"},
        ])
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["state"], "wait")

    def test_subagents_and_compact(self):
        h = run("claude", [
            {"hook_event_name": "SubagentStart", "agent_type": "Explore"},
            {"hook_event_name": "SubagentStart", "agent_type": "Plan"},
            {"hook_event_name": "SubagentStop"},
            {"hook_event_name": "PreCompact", "trigger": "auto"},
            {"hook_event_name": "PostCompact", "trigger": "auto"},
            {"hook_event_name": "Stop"},
        ])
        self.assertEqual([x["sub"] for x in h[:3]], [1, 2, 1])
        self.assertEqual(h[3]["state"], "compact")
        self.assertIn("авто", h[3]["step"])
        self.assertEqual(h[4]["state"], "work")
        self.assertEqual(h[5]["sub"], 0)


class CodexScenarios(unittest.TestCase):
    def test_failure_from_tool_response(self):
        h = run("codex", [
            {"hook_event_name": "PostToolUse", "tool_name": "shell",
             "tool_input": {"command": ["pytest"]}, "tool_response": {"exit_code": 1}},
            {"hook_event_name": "PostToolUse", "tool_name": "shell",
             "tool_input": {"command": ["pytest"]}, "tool_response": "Exit code: 0\nok"},
        ])
        self.assertEqual(h[0]["state"], "error")
        self.assertEqual(h[1]["state"], "work")


class CleanPrompt(unittest.TestCase):
    def test_service_blocks_removed_from_title(self):
        h = run("claude", [{"hook_event_name": "UserPromptSubmit", "prompt":
            "<system-reminder>\nAs you answer the user's questions...\n</system-reminder>\nПочини тесты в модуле оплаты"}])
        self.assertEqual(h[0]["title"], "Почини тесты в модуле оплаты")

    def test_only_service_text_gives_new_task(self):
        h = run("claude-web", [{"hook_event_name": "WebPrompt", "prompt": "<system-reminder>служебное</system-reminder>"}])
        self.assertEqual(h[0]["title"], "Новая задача")

    def test_slash_command_and_plain_brackets(self):
        from adapters.common import clean_prompt
        self.assertEqual(clean_prompt("<command-message>review</command-message><command-name>/review</command-name>"
                                      "<command-args>PR 42</command-args>"), "/review PR 42")
        self.assertEqual(clean_prompt("Почему a < b и b > c?"), "Почему a < b и b > c?")


class AskUserQuestionButton(unittest.TestCase):
    Q = {"questions": [{"question": "Продолжить?", "multiSelect": False,
                        "options": [{"label": "Да, продолжить"}, {"label": "Нет"}]}]}

    def test_step_and_answer(self):
        from adapters.common import describe_permission
        self.assertEqual(describe_permission("AskUserQuestion", self.Q), "Продолжить? → Да, продолжить")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
        try:
            import forward                     # хук сам выбирает язык по настройкам
        finally:
            i18n.set_language("ru")
        self.assertEqual(forward.ask_answers(self.Q), {"Продолжить?": "Да, продолжить"})


class ClaudeWebAdapter(unittest.TestCase):
    def test_permission_command(self):
        h = run("claude-web", [
            {"hook_event_name": "WebPrompt", "prompt": "еще раз"},
            {"hook_event_name": "WebWait", "command": "echo confirm-demo"},
            {"hook_event_name": "WebWait", "message": "Allow Gmail?"},
        ])
        self.assertEqual((h[1]["state"], h[1]["step"]), ("wait", "Разрешить: $ echo confirm-demo"))
        self.assertEqual(h[2]["step"], "Allow Gmail?")

    def test_chat_answer(self):
        h = run("claude-web", [
            {"hook_event_name": "WebPrompt", "prompt": "Объясни  рекурсию", "title": ""},
            {"hook_event_name": "WebBusy", "phase": "thinking"},
            {"hook_event_name": "WebBusy", "phase": "tool", "tool": "Ищу в интернете"},
            {"hook_event_name": "WebBusy", "phase": "writing", "title": "Рекурсия простыми словами"},
            {"hook_event_name": "WebDone"},
        ])
        self.assertEqual((h[0]["state"], h[0]["title"], h[0]["step"]), ("start", "Объясни рекурсию", "Думает…"))
        self.assertEqual((h[1]["state"], h[1]["step"]), ("work", "Думает…"))
        self.assertEqual(h[2]["step"], "Ищу в интернете")
        self.assertEqual((h[3]["step"], h[3]["title"]), ("Пишет ответ", "Рекурсия простыми словами"))
        self.assertEqual((h[4]["state"], h[4]["done"], h[4]["total"], h[4]["step"]), ("done", 1, 1, "Ответ готов"))

    def test_wait_error_and_restart(self):
        h = run("claude-web", [
            {"hook_event_name": "WebBusy", "phase": "writing", "prompt": "Вопрос"},   # демон поднялся посреди ответа
            {"hook_event_name": "WebWait"},
            {"hook_event_name": "WebError", "message": "Ответ прерван"},
        ])
        self.assertEqual((h[0]["state"], h[0]["title"]), ("work", "Вопрос"))
        self.assertEqual((h[1]["state"], h[1]["step"]), ("wait", "Нужно ваше подтверждение"))
        self.assertEqual((h[2]["state"], h[2]["step"]), ("error", "Ответ прерван"))

    def test_done_without_task_ignored(self):
        self.assertEqual(run("claude-web", [{"hook_event_name": "WebDone"}]), [])

    def test_theme_is_claude(self):
        from sessions import Sessions
        s = Sessions(settings=settings())
        s.handle("claude-web", {"hook_event_name": "WebPrompt", "prompt": "Q", "session_id": "tab-1"})
        d = s.display()
        self.assertEqual((d["agent"], d["idle"], d["title"]), ("claude", "robot", "Q"))
        s.handle("claude-web", {"hook_event_name": "SessionEnd", "session_id": "tab-1"})
        self.assertEqual((s.display()["state"], s.display()["agent"]), ("idle", "claude"))


class SessionsTest(unittest.TestCase):
    def setUp(self):
        from sessions import Sessions
        self.now = [0.0]
        self.s = Sessions(clock=lambda: self.now[0], settings=settings())

    def ev(self, agent, sid, **kw):
        self.now[0] += 1
        return self.s.handle(agent, dict(kw, session_id=sid))

    def test_waiting_session_wins_and_others_counted(self):
        self.ev("claude", "a", hook_event_name="UserPromptSubmit", prompt="A")
        self.ev("codex", "b", hook_event_name="UserPromptSubmit", prompt="B")
        d = self.s.display()
        self.assertEqual((d["title"], d["agent"], d["others"]), ("B", "codex", 1))
        self.ev("claude", "a", hook_event_name="PermissionRequest", tool_name="Bash",
                tool_input={"command": "rm -rf x"})
        d = self.s.display()
        self.assertEqual((d["title"], d["state"], d["agent"], d["idle"]), ("A", "wait", "claude", "robot"))
        self.ev("codex", "b", hook_event_name="Stop")
        self.assertEqual(self.s.display()["others"], 0)

    def test_session_end_and_sweep(self):
        self.ev("claude", "a", hook_event_name="UserPromptSubmit", prompt="A")
        self.ev("claude", "a", hook_event_name="SessionEnd", reason="other")
        self.assertEqual(self.s.display()["state"], "idle")
        self.ev("claude", "b", hook_event_name="UserPromptSubmit", prompt="B")
        self.now[0] += 31 * 60
        self.assertTrue(self.s.sweep())
        self.assertEqual(self.s.display()["state"], "idle")

    def test_unchanged_display_not_resent(self):
        self.ev("claude", "a", hook_event_name="UserPromptSubmit", prompt="A")
        self.ev("claude", "b", hook_event_name="UserPromptSubmit", prompt="B")
        self.ev("claude", "a", hook_event_name="PermissionRequest", tool_name="Bash")
        # B работает в фоне, на экране A ждёт — шаг B экран не меняет
        changed = self.ev("claude", "b", hook_event_name="PreToolUse", tool_name="Read",
                          tool_input={"file_path": "x.py"})
        self.assertFalse(changed)


class ButtonApprovals(unittest.TestCase):
    def setUp(self):
        from approvals import Approvals
        from sessions import Sessions
        self.ap = Approvals()
        self.s = Sessions(clock=lambda: 0.0, settings=settings(), approvals=self.ap)
        self.s.handle("claude", {"hook_event_name": "PermissionRequest", "session_id": "A",
                                 "tool_name": "Bash", "tool_input": {"command": "rm -rf build"}})

    def test_display_flags_awaiting_session(self):
        self.assertFalse(self.s.display()["approve"])
        self.ap.begin("claude:A")
        self.assertTrue(self.s.display()["approve"])

    def test_button_resolves_waiting_hook(self):
        import threading
        result = {}
        t = threading.Thread(target=lambda: result.update(d=self.ap.wait("claude:A", 2)))
        t.start()
        while not self.ap.awaiting("claude:A"):
            pass
        self.assertTrue(self.ap.resolve(self.s.top_key(), "allow"))
        t.join()
        self.assertEqual(result["d"], "allow")
        self.assertFalse(self.ap.resolve("claude:A", "deny"))   # второй раз решать нечего

    def test_cancel_when_answered_elsewhere(self):
        import threading
        out = []
        th = threading.Thread(target=lambda: out.append(self.ap.wait("claude-web:tab-1", 5)))
        th.start()
        for _ in range(100):
            if self.ap.awaiting("claude-web:tab-1"):
                break
            threading.Event().wait(0.01)
        self.assertTrue(self.ap.cancel("claude-web:tab-1"))
        th.join(2)
        self.assertEqual(out, [None])
        self.assertFalse(self.ap.cancel("claude-web:tab-1"))

    def test_timeout_returns_none(self):
        self.assertIsNone(self.ap.wait("claude:A", 0.05))

    def test_env_switch(self):
        from approvals import enabled, wait_seconds
        self.assertTrue(enabled(settings()))                              # по умолчанию включено
        self.assertFalse(enabled(settings(AGENT_STATUS_BUTTON_APPROVE="0")))
        self.assertEqual(wait_seconds(settings(AGENT_STATUS_APPROVE_WAIT="500")), 120.0)

    def test_scene_choice_from_button(self):
        self.assertEqual(self.s.display()["idle"], "robot")
        self.assertTrue(self.s.choose_scene("claude", "cursor"))
        self.assertEqual(self.s.display()["idle"], "cursor")
        self.assertFalse(self.s.choose_scene("claude", "typist"))   # у Claude такой сцены нет


class IdleScenes(unittest.TestCase):
    def test_defaults(self):
        from scenes import idle_scene
        self.assertEqual(idle_scene("claude", settings()), "robot")
        self.assertEqual(idle_scene("codex", settings()), "cursor")

    def test_env_choice_and_fallback(self):
        from scenes import idle_scene
        self.assertEqual(idle_scene("claude", settings(AGENT_STATUS_IDLE_CLAUDE="Cursor")), "cursor")
        self.assertEqual(idle_scene("codex", settings(AGENT_STATUS_IDLE_CODEX="typist")), "typist")
        self.assertEqual(idle_scene("codex", settings(AGENT_STATUS_IDLE_CODEX="robot")), "cursor")
        self.assertIsNone(idle_scene("unknown", settings()))


class Language(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("ru")

    def test_english_texts(self):
        i18n.set_language("en")
        h = run("claude", [
            {"hook_event_name": "UserPromptSubmit", "prompt": "Fix tests"},
            {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/a/auth.ts"}},
            {"hook_event_name": "PermissionRequest", "tool_name": "Write", "tool_input": {"file_path": "/a/README.md"}},
            {"hook_event_name": "StopFailure", "error_type": "rate_limit"},
        ])
        self.assertEqual(h[0]["step"], "Thinking…")
        self.assertEqual(h[1]["step"], "Editing auth.ts")
        self.assertEqual(h[2]["step"], "Allow writing README.md?")
        self.assertEqual(h[3]["step"], "Rate limited, pausing")

    def test_unknown_stop_reason(self):
        i18n.set_language("en")
        h = run("claude", [{"hook_event_name": "StopFailure", "error_type": "something_new"}])
        self.assertEqual(h[0]["step"], "Task interrupted")

    def test_lang_sent_to_board(self):
        from sessions import Sessions
        s = Sessions(clock=lambda: 0.0, settings=settings(AGENT_STATUS_LANG="ru"))
        self.assertEqual(s.display()["lang"], "ru")
        self.assertNotIn("title", s.display())       # в ожидании подпись держит сама плата


class Config(unittest.TestCase):
    def test_defaults_and_env(self):
        c = settings()
        self.assertEqual((c["http_port"], c["idle_claude"], c["button_approve"]), (8765, "robot", True))
        c = settings(AGENT_STATUS_PORT="9000", AGENT_STATUS_AUTOSTART="0", AGENT_STATUS_LANG="EN")
        self.assertEqual((c["http_port"], c["autostart"], c["language"]), (9000, False, "en"))

    def test_set_value(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = {"AGENT_STATUS_HOME": d}
            config.set_value("button_approve", "false", env)
            config.set_value("approve_wait", "35", env)
            config.set_value("wifi_host", "192.168.1.7", env)
            c = config.load(env)
            self.assertEqual((c["button_approve"], c["approve_wait"], c["wifi_host"]), (False, 35, "192.168.1.7"))
            config.set_value("button_approve", "on", env)
            self.assertTrue(config.load(env)["button_approve"])
            with open(config.config_path(env), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count("button_approve ="), 1)

    def test_auto_language_from_locale(self):
        self.assertEqual(settings(LANG="ru_RU.UTF-8")["language"], "ru")
        self.assertEqual(settings(LANG="de_DE.UTF-8")["language"], "en")

    def test_file_then_env(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = {"AGENT_STATUS_HOME": d}
            path, created = config.init_file(env)
            self.assertTrue(created)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            text = (text.replace('idle_codex = "cursor"', 'idle_codex = "typist"')
                        .replace("approve_wait = 60", "approve_wait = 45")
                        .replace('language = "auto"', 'language = "ru"'))
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual(config._parse_flat(text), config._parse_toml(text))   # оба разбора согласны
            c = config.load(env)
            self.assertEqual((c["idle_codex"], c["approve_wait"], c["language"]), ("typist", 45, "ru"))
            env["AGENT_STATUS_IDLE_CODEX"] = "cursor"
            self.assertEqual(config.load(env)["idle_codex"], "cursor")      # окружение важнее файла

    def test_fallback_parser(self):
        self.assertEqual(config._parse_value('"a b"'), "a b")
        self.assertEqual(config._parse_value("true"), True)
        self.assertEqual(config._parse_value("12"), 12)

    def test_broken_file_is_reported_not_fatal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = {"AGENT_STATUS_HOME": d}
            path, _ = config.init_file(env)
            with open(path, "a", encoding="utf-8") as f:
                f.write("\nlanguage = = oops\n")
            c = config.load(env)
            self.assertEqual(c["http_port"], 8765)
            self.assertTrue(c["_errors"])

    def test_state_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = {"AGENT_STATUS_HOME": d}
            self.assertEqual(config.load_state(env), {})
            config.save_state({"scene_choice": {"claude": "cursor"}}, env)
            self.assertEqual(config.load_state(env)["scene_choice"]["claude"], "cursor")


if __name__ == "__main__":
    unittest.main()
