"""Bina model ke chalne wale tests (1-2 second). Chalao:  python3 -m unittest discover -s tests

Har test ek ALAG temporary database par chalta hai; assistant.db ko kabhi nahi chhuta.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ["ASSISTANT_DB"] = str(Path(tempfile.mkdtemp(prefix="assistant-tests-")) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent  # noqa: E402
import contacts  # noqa: E402
import habits  # noqa: E402
import planner  # noqa: E402
import router  # noqa: E402
import tools  # noqa: E402
import translit  # noqa: E402
import voice  # noqa: E402
import when  # noqa: E402

NOW = datetime(2026, 11, 8, 7, 30)  # Sunday morning


class WhenParse(unittest.TestCase):
    CASES = {
        "kal shaam 6 baje doodh lena yaad dilao": "2026-11-09 18:00",
        "parso subah 10 baje dentist appointment hai": "2026-11-10 10:00",
        "15 tareekh ko shaam 6 baje rent dena": "2026-11-15 18:00",
        "1 december ko subah 10 baje interview": "2026-12-01 10:00",
        "kal subah gym, shaam 6 baje doodh lena": "2026-11-09 18:00",
        "aaj raat 12 baje dawai": "2026-11-09 00:00",
        "ek ghante baad chai banana": "2026-11-08 08:30",
        "30 minute ke baad paani peena": "2026-11-08 08:00",
        "do din baad dentist": "2026-11-10",
        "dus baje meeting": "2026-11-08 10:00",
        "dedh baje lunch": "2026-11-08 13:30",
        "kal do baje meeting": "2026-11-09 14:00",
        "perso subah 10 bajay dentist": "2026-11-10 10:00",
    }
    NOT_TIMES = {
        "kal sham kaa doodh lanaee ki yaad dilanae wala reminder hataa do": "2026-11-09",  # "do" != 2 baje
        "kal Rahul ko saade teen sau rupaye dene hain": "2026-11-09",                     # rakam, samay nahi
        "kal paune do kilo chawal lana": "2026-11-09",
        "kal raat 7 ghante soya": "2026-11-09",
    }

    def test_times(self):
        for text, want in {**self.CASES, **self.NOT_TIMES}.items():
            with self.subTest(text=text):
                self.assertEqual(when.parse(text, NOW), want)

    def test_bare_hour_is_the_next_one(self):
        morning = datetime(2026, 11, 13, 9, 44)
        self.assertEqual(when.parse("book read karna yaad dilana 8 baje", morning), "2026-11-13 20:00")  # aaj raat
        self.assertEqual(when.parse("subah 8 baje gym", morning), "2026-11-14 08:00")
        self.assertEqual(when.parse("8 baje gym", datetime(2026, 11, 13, 21, 0)), "2026-11-14 08:00")

    def test_no_time_words(self):
        self.assertIsNone(when.parse("mummy ko phone karna hai", NOW))


class Decision(unittest.TestCase):
    def test_yes_no_unclear(self):
        cases = {"haan": "yes", "haan hata do": "yes", "haan, hata do": "yes", "ok": "yes", "theek hai": "yes",
                 "nahi": "no", "nahi yaar": "no", "mat hatao": "no",
                 "haan?": "unclear", "ji?": "unclear", "ha ha": "unclear",
                 "haan gym bhi yaad dilao": None, "nahi dentist wala nahi doodh wala": None}
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(agent._decision(text), want)


class Titles(unittest.TestCase):
    def test_clean_title(self):
        cases = {"dentist subah 10 baje yaad dilana": "dentist", "mujhe phone karna hai yaad dila do": "phone karna",
                 "kal shaam 6 baje doodh lena yaad dilao": "doodh lena",
                 "Rahul ko saade teen sau rupaye dene": "Rahul ko saade teen sau rupaye dene"}
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(planner.clean_title(text), want)


class Routing(unittest.TestCase):
    def test_remove_vs_create(self):
        self.assertEqual(router.route("doodh lena wala reminder hata do")["tools"], ["remove_task"])
        self.assertEqual(router.route("kal sham kaa doodh lanaee ki yaad dilanae wala reminder hataa do")["tools"], ["remove_task"])
        self.assertNotIn("remove_task", router.route("kal Netflix subscription cancel karna yaad dilao")["tools"])

    def test_devanagari_delete(self):
        self.assertEqual(router.route(translit.to_roman("डेंटिस्ट वाला रिमाइंडर डिलीट कर दो"))["tools"], ["remove_task"])

    def test_chat_gets_no_tools(self):
        self.assertEqual(router.route("aaj ka din kaisa raha")["tools"], [])


class DeleteSafety(unittest.TestCase):
    def test_reused_id_never_deletes_another_task(self):
        first = planner.add_task("doodh lena")
        tools.confirm_delete("task", first, "doodh lena")
        second = planner.add_task("gym jana")  # SQLite wahi id dobara de sakta hai
        with self.assertRaises(ValueError):
            tools.confirm_delete("task", second, "doodh lena")  # purani screen ka naam: kuch nahi hatna chahiye
        self.assertIn("gym jana", [t["title"] for t in planner.list_tasks()])

    def test_remove_tools_only_ask(self):
        task_id = planner.add_task("dentist appointment")
        result = tools.run_tool("remove_task", {"task": "dentist wala reminder"})
        self.assertIn('"confirm"', result)
        self.assertIn(task_id, [t["id"] for t in planner.list_tasks()])
        self.assertNotIn("confirm_delete", tools.TOOL_FUNCTIONS)  # model asli delete kabhi nahi bula sakta

    def test_question_mark_is_not_a_yes(self):
        planner.add_task("bijli ka bill bharna")
        history = []
        tools_run = []
        history.append({"role": "user", "content": "x"})
        history.append({"role": "assistant", "content": "Pakka?", "_pending": {
            "kind": "task", "id": planner.list_tasks()[-1]["id"], "name": "bijli ka bill bharna",
            "label": "bijli ka bill bharna", "token": "t1", "ts": datetime.now().timestamp()}})
        agent.run_turn(history, "haan?", on_tool=lambda *a: tools_run.append(a[0]))
        self.assertNotIn("confirm_delete", tools_run)
        self.assertIn("bijli ka bill bharna", [t["title"] for t in planner.list_tasks()])


class VoiceCorrection(unittest.TestCase):
    def test_fixes_only_known_mishearings(self):
        contacts.add_contact("Jim", "9811111111", [])
        habits.add_habit("reading")
        self.assertEqual(voice.correct("mujhe phoon karna hai aaad diti ho"), "mujhe phone karna hai yaad diti ho")
        self.assertEqual(voice.correct("chai banana yaad dilao"), "chai banana yaad dilao")
        self.assertEqual(voice.correct("kal contract sign karna hai"), "kal contract sign karna hai")
        self.assertEqual(voice.correct("jim ko call karo"), "jim ko call karo")  # saved naam kabhi nahi badalta

    def test_whisper_artifacts(self):  # asli recordings mein aaye: prompt ka label, "aaah", "chye vajay"
        self.assertEqual(voice.correct(voice._clean("mera: aaah kal bijli ka bil bharna. mera:")), "kal bijli ka bill bharna.")
        self.assertEqual(voice.correct(voice._clean("walk pe jana yaad dilana chye vajay.")), "walk pe jana yaad dilana 6 baje.")


class Translit(unittest.TestCase):
    def test_hinglish(self):
        self.assertEqual(translit.to_roman("मेरा छाता कहाँ है"), "mera chhata kahan hai")
        self.assertEqual(translit.to_roman("मम्मी को कॉल करो"), "mummy ko call karo")


class ReviewRegressions(unittest.TestCase):
    """Aakhri review ki galtiyan dobara na aayein (model ki jagah fake model: tez aur pakka)."""

    def fake_model(self, calls):
        replies = iter([{"role": "assistant", "content": "", "tool_calls": calls},
                        {"role": "assistant", "content": "ok"}])
        original = agent.llm.chat
        agent.llm.chat = lambda messages, tools=None: next(replies)
        self.addCleanup(setattr, agent.llm, "chat", original)

    def test_empty_token_never_deletes(self):
        planner.add_task("gas cylinder book karna")
        task = [t for t in planner.list_tasks() if t["title"] == "gas cylinder book karna"][0]
        history = [{"role": "user", "content": "x"},
                   {"role": "assistant", "content": "Pakka?", "_pending": {"kind": "task", "id": task["id"],
                    "name": task["title"], "label": task["title"], "token": "abc", "ts": datetime.now().timestamp()}}]
        agent.run_turn(history, "haan", confirm_token="")  # "" = is tab mein koi sawal nahi dikh raha
        self.assertIn("gas cylinder book karna", [t["title"] for t in planner.list_tasks()])

    def test_remove_plus_add_in_one_message_can_be_confirmed(self):
        planner.add_task("chai patti lana")
        self.fake_model([
            {"function": {"name": "remove_task", "arguments": {"task": "chai patti"}}},
            {"function": {"name": "add_task", "arguments": {"title": "gym", "due": "2030-01-01 06:00"}}},
        ])
        history = []
        agent.run_turn(history, "chai patti wala reminder hata do aur kal 6 baje gym yaad dilao")
        self.assertIn("_pending", history[-1])
        gym = [t for t in planner.list_tasks() if t["title"] == "gym"][0]
        self.assertTrue(gym["due_at"].endswith("18:00"))  # "kal 6 baje" code se, model ka galat samay nahi
        agent.run_turn(history, "haan")
        self.assertNotIn("chai patti lana", [t["title"] for t in planner.list_tasks()])

    def test_task_name_plus_hata_do_offers_remove_tools(self):
        tools_offered = router.route("doodh lena hata do")["tools"]
        self.assertIn("remove_task", tools_offered)
        self.assertNotIn("complete_task", tools_offered)
        self.assertNotIn("remove_task", router.route("cheeni hatana hai diet se")["tools"])

    def test_schema_comes_back_if_db_file_is_replaced(self):
        import db
        path = Path(os.environ["ASSISTANT_DB"])
        planner.add_task("temp")
        for suffix in ("", "-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
        with db.connect() as conn:  # nayi khaali file: tables dobara banne chahiye
            conn.execute("SELECT COUNT(*) FROM tasks").fetchone()


if __name__ == "__main__":
    unittest.main()
