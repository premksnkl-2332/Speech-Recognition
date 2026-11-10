"""Voice To-Do Manager - command line entry point.

Examples:
    python main.py                 # talk to it through the microphone
    python main.py --text          # type commands instead (no microphone needed)
    python main.py --file demo.wav # run one command from a recording
"""
from __future__ import annotations

import argparse
import sys

from voice_todo.app import HELP_TEXT, TodoApp
from voice_todo.store import TaskStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a to-do list by voice.")
    parser.add_argument("--text", action="store_true",
                        help="type commands instead of speaking them")
    parser.add_argument("--file", metavar="AUDIO",
                        help="run a single command from a WAV/FLAC/AIFF file")
    parser.add_argument("--language", default="en-IN",
                        help="recognition language code (default: en-IN)")
    parser.add_argument("--data", default="tasks.json",
                        help="file where tasks are saved (default: tasks.json)")
    parser.add_argument("--no-speak", action="store_true",
                        help="print replies only, do not read them aloud")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    app = TodoApp(TaskStore(args.data))

    speaker = None
    if not args.no_speak and not args.text:
        from voice_todo.speech import Speaker
        speaker = Speaker()

    def reply(message: str) -> None:
        print(message)
        if speaker is not None:
            # Read only the first line aloud for long lists, then the items.
            speaker.say(message.replace("[x]", "done,").replace("[ ]", ""))

    # ----- one command from an audio file -----
    if args.file:
        from voice_todo.speech import SpeechServiceError, transcribe_file
        try:
            sentence = transcribe_file(args.file, args.language)
        except SpeechServiceError as exc:
            print(exc)
            return 1
        if not sentence:
            print("Could not understand the recording.")
            return 1
        print(f"Heard: {sentence}")
        reply(app.handle(sentence))
        return 0

    # ----- typed commands -----
    if args.text:
        print("Voice To-Do Manager (text mode). " + HELP_TEXT)
        while app.running:
            try:
                sentence = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if sentence.strip():
                print(app.handle(sentence))
        return 0

    # ----- microphone -----
    try:
        from voice_todo.speech import Listener, SpeechServiceError
        print("Calibrating microphone, please stay quiet for a second...")
        listener = Listener(language=args.language)
    except ImportError:
        print("Voice mode needs extra packages. Run: pip install -r requirements.txt\n"
              "Or try text mode: python main.py --text")
        return 1
    except OSError as exc:
        print(f"No working microphone found ({exc}). Try: python main.py --text")
        return 1

    reply("Voice To-Do Manager is ready. Say help to hear the commands.")
    while app.running:
        print("\nListening...")
        try:
            sentence = listener.listen()
        except SpeechServiceError as exc:
            print(exc)
            return 1
        except KeyboardInterrupt:
            print()
            break
        if not sentence:
            print("(did not catch that)")
            continue
        print(f"Heard: {sentence}")
        reply(app.handle(sentence))
    return 0


if __name__ == "__main__":
    sys.exit(main())
