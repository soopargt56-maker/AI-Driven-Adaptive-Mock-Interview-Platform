from __future__ import annotations

import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict] = []

    def insert_one(self, document: dict) -> None:
        self.documents.append(document)

    def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                if not projection:
                    return document
                result = dict(document)
                for key, flag in projection.items():
                    if flag == 0:
                        result.pop(key, None)
                return result
        return None

    def update_one(self, query: dict, update: dict) -> None:
        document = self.find_one(query)
        if not document:
            return

        for key, value in update.get("$set", {}).items():
            self._set_nested(document, key, value)

        for key, value in update.get("$addToSet", {}).items():
            current = document.setdefault(key, [])
            if value not in current:
                current.append(value)

    @staticmethod
    def _set_nested(document: dict, key: str, value) -> None:
        parts = key.split(".")
        target = document
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value


class FakeDatabase(dict):
    def __init__(self) -> None:
        super().__init__()
        self["candidates"] = FakeCollection()
        self["sessions"] = FakeCollection()


class ApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDatabase()
        self.client = TestClient(app)

        self.resume_patcher = patch(
            "backend.routes.resume.load_module",
            return_value=SimpleNamespace(parse_resume=lambda _: ["Python", "React"]),
        )
        self.domain_patcher = patch(
            "backend.routes.resume.map_skills_to_domains",
            return_value={"Python": "python_core", "React": "web_frontend"},
        )
        self.resume_db_patcher = patch(
            "backend.routes.resume.get_database", return_value=self.db
        )
        self.session_db_patcher = patch(
            "backend.routes.session.get_database", return_value=self.db
        )
        self.answer_db_patcher = patch(
            "backend.routes.answer.get_database", return_value=self.db
        )
        self.dashboard_db_patcher = patch(
            "backend.routes.dashboard.get_database", return_value=self.db
        )
        self.question_patcher = patch(
            "backend.routes.session._get_next_question",
            side_effect=self._fake_question_bank,
        )
        self.answer_question_patcher = patch(
            "backend.routes.answer._get_next_question",
            side_effect=self._fake_question_bank,
        )
        self.pipeline_patcher = patch(
            "backend.routes.answer.run_scoring_pipeline",
            return_value={
                "svm_label": "Good",
                "nlp_score": 82.0,
                "kg_score": 78.0,
                "ner_entities": ["binary search", "time complexity"],
                "final_score": 80.5,
                "feedback": {
                    "content": ["Clear explanation of the search space reduction."],
                    "strengths": ["Explained sorted-array prerequisite"],
                    "next_step": "Add edge cases and iterative vs recursive tradeoffs.",
                },
                "metadata": {},
            },
        )

        for patcher in (
            self.resume_patcher,
            self.domain_patcher,
            self.resume_db_patcher,
            self.session_db_patcher,
            self.answer_db_patcher,
            self.dashboard_db_patcher,
            self.question_patcher,
            self.answer_question_patcher,
            self.pipeline_patcher,
        ):
            patcher.start()

    def tearDown(self) -> None:
        for patcher in (
            self.pipeline_patcher,
            self.answer_question_patcher,
            self.question_patcher,
            self.dashboard_db_patcher,
            self.answer_db_patcher,
            self.session_db_patcher,
            self.resume_db_patcher,
            self.domain_patcher,
            self.resume_patcher,
        ):
            patcher.stop()

    @staticmethod
    def _fake_question_bank(
        *, skill: str, sub_domain: str | None, difficulty: str, asked: list[str]
    ) -> dict:
        round_number = len(asked) + 1
        return {
            "question": f"{difficulty.title()} {skill} question {round_number}",
            "ideal_answer": "Reference answer",
            "ideal_keywords": "binary search complexity sorted",
            "skill": skill,
            "sub_domain": sub_domain,
        }

    def test_full_backend_contract(self) -> None:
        resume_response = self.client.post(
            "/resume",
            files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
        )
        self.assertEqual(resume_response.status_code, 200)
        resume_payload = resume_response.json()
        self.assertIn("candidate_id", resume_payload)
        self.assertEqual(resume_payload["skills"], ["Python", "React"])
        self.assertEqual(
            resume_payload["domain_profile"],
            {"Python": "python_core", "React": "web_frontend"},
        )

        start_response = self.client.post(
            "/session/start",
            json={
                "candidate_id": resume_payload["candidate_id"],
                "skill": "Python",
                "sub_domain": "python_core",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_payload = start_response.json()
        self.assertEqual(start_payload["round"], 1)
        self.assertIn("session_id", start_payload)
        self.assertIn("question", start_payload)
        self.assertIn("difficulty", start_payload)

        answer_response = self.client.post(
            "/session/answer",
            json={
                "session_id": start_payload["session_id"],
                "round": 1,
                "answer_text": "Binary search works on sorted arrays and halves the search space.",
                "cos_similarity": 0.84,
                "length_ratio": 0.72,
                "aligned_score": 88.0,
                "word_count": 11,
                "engagement_label": "High Engagement",
                "wpm": 132.0,
                "pause_count": 1,
            },
        )
        self.assertEqual(answer_response.status_code, 200)
        answer_payload = answer_response.json()
        self.assertEqual(answer_payload["svm_label"], "Good")
        self.assertEqual(answer_payload["nlp_score"], 82.0)
        self.assertEqual(answer_payload["kg_score"], 78.0)
        self.assertEqual(answer_payload["final_score"], 80.5)
        self.assertIn("feedback", answer_payload)
        self.assertIn("next_question", answer_payload)
        self.assertIn("next_difficulty", answer_payload)
        self.assertIn("elo_after", answer_payload)
        self.assertIn("difficulty_change", answer_payload)

        dashboard_response = self.client.get(f"/dashboard/{start_payload['session_id']}")
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard_payload = dashboard_response.json()
        self.assertEqual(dashboard_payload["session_id"], start_payload["session_id"])
        self.assertIn("rounds", dashboard_payload)
        self.assertIn("averages", dashboard_payload)
        self.assertIn("breakdown", dashboard_payload)
        self.assertIn("elo_progression", dashboard_payload)
        self.assertIn("difficulty_progression", dashboard_payload)
        self.assertEqual(
            dashboard_payload["next_step"],
            "Add edge cases and iterative vs recursive tradeoffs.",
        )


if __name__ == "__main__":
    unittest.main()
