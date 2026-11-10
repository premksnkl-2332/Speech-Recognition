"""Glue between the parser and the task store.

TodoApp.handle() takes a sentence and returns the reply to show and speak.
It has no microphone or speaker code, so the full command flow can be tested.
"""
from __future__ import annotations

import datetime as _dt
from typing import Callable, Optional

from .parser import Command, parse_command
from .store import Task, TaskStore

HELP_TEXT = (
    "You can say: add buy milk. Show my tasks. Mark task two as done. "
    "Delete task one. Clear completed tasks. Or say exit to stop."
)


class TodoApp:
    def __init__(self, store: TaskStore,
                 today: Callable[[], _dt.date] = _dt.date.today):
        self.store = store
        self._today = today
        self.running = True

    # ---------- formatting ----------
    def _describe(self, task: Task) -> str:
        extras = []
        if task.priority == "high":
            extras.append("high priority")
        if task.due:
            today = self._today()
            due = _dt.date.fromisoformat(task.due)
            if due == today:
                extras.append("due today")
            elif due == today + _dt.timedelta(days=1):
                extras.append("due tomorrow")
            elif due < today:
                extras.append("overdue since " + task.due)
            else:
                extras.append("due " + task.due)
        return task.text + (" (" + ", ".join(extras) + ")" if extras else "")

    def format_list(self, scope: str = "all") -> str:
        tasks = self.store.tasks
        if not tasks:
            return "Your to-do list is empty."
        rows = []
        for number, task in enumerate(tasks, start=1):
            if scope == "pending" and task.done:
                continue
            if scope == "done" and not task.done:
                continue
            box = "[x]" if task.done else "[ ]"
            rows.append(f"{number}. {box} {self._describe(task)}")
        if not rows:
            return ("You have no pending tasks." if scope == "pending"
                    else "You have no completed tasks.")
        pending = self.store.pending_count()
        plural = "task" if pending == 1 else "tasks"
        header = f"You have {pending} pending {plural}."
        return header + "\n" + "\n".join(rows)

    # ---------- command handling ----------
    def _locate(self, command: Command) -> Optional[int]:
        if command.index is not None:
            return self.store.resolve_index(command.index)
        return self.store.find(command.text)

    def _missing(self, command: Command) -> str:
        if command.index is not None:
            if command.index == -1:
                return "Your to-do list is empty."
            return f"There is no task {command.index}."
        return f"I could not find a task matching '{command.text}'."

    def handle(self, sentence: str) -> str:
        """Run one spoken sentence and return the reply."""
        command = parse_command(sentence)
        action = command.action

        if action == "add":
            due_iso = None
            if command.due:
                day = self._today()
                if command.due == "tomorrow":
                    day += _dt.timedelta(days=1)
                due_iso = day.isoformat()
            number = self.store.add(
                command.text, command.priority, due_iso,
                created=self._today().isoformat(),
            )
            return f"Added task {number}: {self._describe(self.store.tasks[-1])}."

        if action == "list":
            return self.format_list(command.scope)

        if action == "complete":
            position = self._locate(command)
            if position is None:
                return self._missing(command)
            if self.store.tasks[position].done:
                return f"Task {position + 1} is already done."
            task = self.store.complete(position)
            return f"Marked task {position + 1} as done: {task.text}."

        if action == "delete":
            position = self._locate(command)
            if position is None:
                return self._missing(command)
            task = self.store.delete(position)
            return f"Deleted task {position + 1}: {task.text}."

        if action == "clear_done":
            count = self.store.clear_done()
            if count == 0:
                return "There are no completed tasks to clear."
            return f"Cleared {count} completed {'task' if count == 1 else 'tasks'}."

        if action == "clear_all":
            count = self.store.clear_all()
            return f"Deleted all {count} tasks." if count else "Your to-do list is already empty."

        if action == "help":
            return HELP_TEXT

        if action == "exit":
            self.running = False
            return "Goodbye."

        return "Sorry, I did not understand that. Say help to hear the commands."
