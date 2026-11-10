"""Turn a transcribed sentence into a structured to-do command.

The parser is rule based (regular expressions), so it works offline, needs no
training data and is easy to unit test. It never touches the microphone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# Spoken numbers and ordinals -> task position. "last" maps to -1.
_NUMBERS = {
    "one": 1, "first": 1,
    "two": 2, "second": 2,
    "three": 3, "third": 3,
    "four": 4, "fourth": 4,
    "five": 5, "fifth": 5,
    "six": 6, "sixth": 6,
    "seven": 7, "seventh": 7,
    "eight": 8, "eighth": 8,
    "nine": 9, "ninth": 9,
    "ten": 10, "tenth": 10,
    "last": -1,
}
_NUM = r"\d+(?:st|nd|rd|th)?|" + "|".join(_NUMBERS)

_TARGET_RE = re.compile(
    rf"^(?:the |my )?(?:task |item )?(?:number )?({_NUM})(?: task| item| one)?$"
)

_EXIT_PHRASES = {"exit", "quit", "stop", "bye", "goodbye", "stop listening", "close"}
_HELP_PHRASES = {"help", "what can i say", "what can you do", "commands"}

_CLEAR_DONE_RE = re.compile(
    r"^(?:clear|remove|delete) (?:all )?(?:the |my )?(?:completed|done|finished)(?: tasks?)?$"
)
_CLEAR_ALL_RE = re.compile(
    r"^(?:clear|remove|delete) (?:all|everything)(?: (?:the |my )?tasks?)?$"
)
_LIST_RE = re.compile(
    r"^(?:show|list|read|display|tell me|what are|what's|whats|what is|how many)\b(.*)$"
)
_LIST_KEYWORDS_RE = re.compile(
    r"\b(?:tasks?|to do|todo|todos|list|pending|left|remaining|completed|done|finished)\b"
)
_COMPLETE_RE = re.compile(
    r"^(?:complete|finish|check off|tick off|tick|mark|done with|"
    r"i finished|i completed|i have finished|i have completed)\s+(.+)$"
)
_IS_DONE_RE = re.compile(r"^(.+?) is (?:done|finished|complete|completed)$")
_DELETE_RE = re.compile(r"^(?:delete|remove|cancel|erase|drop)\s+(.+)$")
_ADD_RE = re.compile(
    r"^(?:add|create|new task|note|remember to|remind me to|i need to|i have to|"
    r"i must|i should|don't forget to|do not forget to)\s+(.+)$"
)

_POLITE_PREFIX_RE = re.compile(
    r"^(?:(?:please|hey|okay|ok|can you|could you|would you)\s+)+"
)
_ADD_FILLER_RE = re.compile(
    r"^(?:a |an )?(?:new )?(?:task|item|to do|todo)"
    r"(?: to| called| named| that says)?\s+"
)
_ADD_TAIL_RE = re.compile(
    r"\s+(?:to|in|on) (?:my |the )?(?:to do |todo |task )?list$"
)
_DONE_TAIL_RE = re.compile(
    r"\s+(?:as |is )?(?:done|complete|completed|finished|off)$"
)
_DUE_TAIL_RE = re.compile(r"\s+(?:by |due |for )?(today|tonight|tomorrow)$")
_PRIORITY_TAIL_RE = re.compile(
    r"\s+(?:(?:with |as |at )?high priority|(?:it's |it is |its |as )?urgent(?:ly)?)$"
)
_PRIORITY_HEAD_RE = re.compile(
    r"^(?:urgent(?:ly)?|important|high priority)(?: task)?(?: to)?\s+"
)


@dataclass
class Command:
    """A parsed voice command.

    action: add, complete, delete, list, clear_done, clear_all, help, exit, unknown
    text:   task text (add) or the words used to find a task (complete/delete)
    index:  1-based task position, or -1 for "last"
    scope:  for list: "all", "pending" or "done"
    """

    action: str
    text: str = ""
    index: Optional[int] = None
    priority: str = "normal"
    due: Optional[str] = None  # "today" or "tomorrow"
    scope: str = "all"


def normalize(sentence: str) -> str:
    """Lower-case, drop punctuation and polite filler words."""
    text = sentence.lower().strip()
    text = text.replace("’", "'")
    text = re.sub(r"[,!?;]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = _POLITE_PREFIX_RE.sub("", text)
    text = re.sub(r"\s+please$", "", text)
    return text.strip()


def _to_index(token: str) -> int:
    if token in _NUMBERS:
        return _NUMBERS[token]
    return int(re.sub(r"(?:st|nd|rd|th)$", "", token))


def _parse_target(rest: str) -> Tuple[Optional[int], str]:
    """Work out which task the user means: a position or some words."""
    rest = rest.strip()
    match = _TARGET_RE.match(rest)
    if match:
        return _to_index(match.group(1)), ""
    words = re.sub(r"^(?:the |my )?(?:task |item )(?:called |named )?", "", rest)
    return None, words.strip()


def _parse_add(rest: str) -> Command:
    # Trailing space lets "add a task" (with nothing after it) reduce to empty.
    text = _ADD_FILLER_RE.sub("", rest.strip() + " ").strip()
    text = _ADD_TAIL_RE.sub("", text)
    priority = "normal"
    due = None

    head = _PRIORITY_HEAD_RE.match(text)
    if head:
        priority = "high"
        text = text[head.end():]

    # Run twice so "... tomorrow with high priority" and the reverse both work.
    for _ in range(2):
        match = _PRIORITY_TAIL_RE.search(text)
        if match:
            priority = "high"
            text = text[: match.start()]
        match = _DUE_TAIL_RE.search(text)
        if match:
            due = "tomorrow" if match.group(1) == "tomorrow" else "today"
            text = text[: match.start()]

    text = text.strip()
    if not text:
        return Command("unknown")
    return Command("add", text=text, priority=priority, due=due)


def parse_command(sentence: str) -> Command:
    """Convert one transcribed sentence into a Command."""
    text = normalize(sentence)
    if not text:
        return Command("unknown")

    if text in _EXIT_PHRASES:
        return Command("exit")
    if text in _HELP_PHRASES:
        return Command("help")

    # Order matters: "remove completed tasks" must not be read as a delete.
    if _CLEAR_DONE_RE.match(text):
        return Command("clear_done")
    if _CLEAR_ALL_RE.match(text):
        return Command("clear_all")

    match = _LIST_RE.match(text)
    if match:
        rest = match.group(1).strip()
        if not rest or _LIST_KEYWORDS_RE.search(rest):
            if re.search(r"\b(?:pending|left|remaining)\b", rest):
                return Command("list", scope="pending")
            if re.search(r"\b(?:completed|done|finished)\b", rest):
                return Command("list", scope="done")
            return Command("list", scope="all")

    match = _COMPLETE_RE.match(text)
    if match:
        rest = _DONE_TAIL_RE.sub("", match.group(1))
        index, words = _parse_target(rest)
        return Command("complete", text=words, index=index)

    match = _IS_DONE_RE.match(text)
    if match:
        index, words = _parse_target(match.group(1))
        return Command("complete", text=words, index=index)

    match = _DELETE_RE.match(text)
    if match:
        index, words = _parse_target(match.group(1))
        return Command("delete", text=words, index=index)

    match = _ADD_RE.match(text)
    if match:
        return _parse_add(match.group(1))

    return Command("unknown", text=text)
