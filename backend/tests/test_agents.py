import logging
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Ensure backend/ is on sys.path so 'app' package is importable when running
# `pytest backend` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents import researcher_node
from app.tools import format_search_results


def _patch_call_llm():
    # Return the received prompt so tests can inspect aggregated notes.
    return patch("app.agents.call_llm", side_effect=lambda system, user, max_tokens=1200: user)


def _base_state(sub_questions):
    return {
        "topic": "t",
        "sub_questions": sub_questions,
        "research_notes": "",
        "draft": "",
        "review_notes": "",
        "approved": False,
        "revised": False,
        "steps": [],
    }


def test_researcher_sequential_ordering_preserved():
    def slow_search(query):
        time.sleep(0.05)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=slow_search), _patch_call_llm():
        state = researcher_node(_base_state(["a", "b", "c"]))

    combined = state["research_notes"]
    assert combined.index("Sub-question: a") < combined.index("Sub-question: b") < combined.index("Sub-question: c")


def test_researcher_partial_failure_continues():
    def search(query):
        if query == "b":
            raise RuntimeError("search exploded")
        return [{"title": query, "url": "u", "snippet": "ok"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        state = researcher_node(_base_state(["a", "b", "c"]))

    notes = state["research_notes"]
    assert "Sub-question: a" in notes
    assert "Sub-question: b" in notes
    assert "Search failed: search exploded" in notes
    assert "Sub-question: c" in notes
    assert state["steps"][-1]["agent"] == "researcher"


def test_researcher_empty_sub_questions():
    with _patch_call_llm():
        state = researcher_node(_base_state([]))

    assert state["research_notes"] == ""
    assert len(state["steps"]) == 1
    assert state["steps"][0]["agent"] == "researcher"


def test_researcher_concurrent_execution():
    timings = {}

    def search(query):
        timings[query] = time.perf_counter()
        time.sleep(0.1)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        start = time.perf_counter()
        state = researcher_node(_base_state(["a", "b", "c"]))
        duration = time.perf_counter() - start

    # Sequential would be ~0.3s; concurrent should be closer to ~0.1s.
    assert duration < 0.25
    assert all(q in timings for q in ["a", "b", "c"])
    assert state["research_notes"]


def test_researcher_logs(caplog):
    def search(query):
        time.sleep(0.01)
        return [{"title": query, "url": "u", "snippet": "s"}]

    with patch("app.agents.web_search", side_effect=search), _patch_call_llm():
        with caplog.at_level(logging.DEBUG, logger="app.agents"):
            researcher_node(_base_state(["q1"]))

    assert any("Starting 1 concurrent research task(s)" in r.message for r in caplog.records)
    assert any("Submitting search for: q1" in r.message for r in caplog.records)
    assert any("Search completed for 'q1'" in r.message for r in caplog.records)


def test_format_search_results_empty():
    assert format_search_results([]) == "No results found."


def test_format_search_results_formats():
    results = [{"title": "t", "url": "u", "snippet": "s"}]
    assert "- t: s (u)" in format_search_results(results)