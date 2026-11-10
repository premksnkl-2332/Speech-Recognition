"""Task storage: an ordered list of tasks saved to a JSON file."""
from __future__ import annotations

import difflib
import json
import os
from dataclasses import asdict, dataclass
from typing import List, Optional


@dataclass
class Task:
    text: str
    done: bool = False
    priority: str = "normal"
    due: Optional[str] = None  # ISO date, e.g. "2026-11-11"
    created: str = ""


class TaskStore:
    """Keeps tasks in memory and mirrors every change to disk.

    Tasks are addressed by their 1-based position in the list, which is the
    number the user hears when the list is read out.
    """

    def __init__(self, path: Optional[str] = "tasks.json"):
        self.path = path
        self.tasks: List[Task] = []
        self.load()

    # ---------- persistence ----------
    def load(self) -> None:
        self.tasks = []
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return  # A damaged file should not stop the app from starting.
        for item in raw:
            self.tasks.append(
                Task(
                    text=item.get("text", ""),
                    done=bool(item.get("done", False)),
                    priority=item.get("priority", "normal"),
                    due=item.get("due"),
                    created=item.get("created", ""),
                )
            )

    def save(self) -> None:
        if not self.path:
            return
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump([asdict(task) for task in self.tasks], handle, indent=2)

    # ---------- lookups ----------
    def resolve_index(self, index: int) -> Optional[int]:
        """Convert a spoken position (1-based, -1 = last) to a list index."""
        if not self.tasks:
            return None
        if index == -1:
            return len(self.tasks) - 1
        if 1 <= index <= len(self.tasks):
            return index - 1
        return None

    def find(self, words: str, prefer_pending: bool = True) -> Optional[int]:
        """Find the task that best matches some spoken words.

        Tries an exact match, then a substring match, then a fuzzy match so a
        slightly misheard word still finds the right task.
        """
        words = words.strip().lower()
        if not words or not self.tasks:
            return None

        order = list(range(len(self.tasks)))
        if prefer_pending:
            order.sort(key=lambda i: self.tasks[i].done)

        for i in order:
            if self.tasks[i].text.lower() == words:
                return i
        for i in order:
            text = self.tasks[i].text.lower()
            if words in text or text in words:
                return i

        best, best_score = None, 0.0
        for i in order:
            score = difflib.SequenceMatcher(
                None, words, self.tasks[i].text.lower()
            ).ratio()
            if score > best_score:
                best, best_score = i, score
        return best if best_score >= 0.6 else None

    # ---------- changes ----------
    def add(self, text: str, priority: str = "normal",
            due: Optional[str] = None, created: str = "") -> int:
        self.tasks.append(Task(text=text, priority=priority, due=due, created=created))
        self.save()
        return len(self.tasks)  # 1-based position of the new task

    def complete(self, position: int) -> Task:
        task = self.tasks[position]
        task.done = True
        self.save()
        return task

    def delete(self, position: int) -> Task:
        task = self.tasks.pop(position)
        self.save()
        return task

    def clear_done(self) -> int:
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if not task.done]
        self.save()
        return before - len(self.tasks)

    def clear_all(self) -> int:
        count = len(self.tasks)
        self.tasks = []
        self.save()
        return count

    def pending_count(self) -> int:
        return sum(1 for task in self.tasks if not task.done)
