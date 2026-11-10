# Voice To-Do Manager

Manage your to-do list by talking. Say *"add buy milk"*, *"mark task two as done"* or *"show my tasks"* and the app updates the list and reads the reply back to you.

Built with Python, the `SpeechRecognition` library (Google Web Speech API) for speech-to-text and `pyttsx3` for text-to-speech.

## Features

- Add, complete, delete and list tasks using natural spoken sentences
- Understands numbers and ordinals: "task 2", "task two", "the second task", "the last task"
- Finds tasks by name even when a word is misheard ("by groceries" still matches "buy groceries")
- Priority and due dates by voice: "add submit the report tomorrow with high priority"
- Spoken replies (text-to-speech)
- Tasks are saved to `tasks.json`, so they are still there next time
- Text mode and audio-file mode for testing without a microphone

## Setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/<your-username>/voice-todo-manager.git
cd voice-todo-manager
pip install -r requirements.txt
```

`PyAudio` is needed for the microphone. If it fails to install:

- **Windows:** `pip install pipwin` then `pipwin install pyaudio`
- **Ubuntu/Debian:** `sudo apt install portaudio19-dev python3-pyaudio`
- **macOS:** `brew install portaudio` then `pip install pyaudio`

Speech recognition uses Google's online service, so an internet connection is needed in voice mode.

## Usage

```bash
python main.py                  # voice mode (microphone)
python main.py --text           # type the commands instead
python main.py --file demo.wav  # run one command from a recording
python main.py --language en-US # change the accent/language (default en-IN)
python main.py --no-speak       # do not read replies aloud
```

## Voice commands

| You say | What happens |
| --- | --- |
| "Add buy milk" / "Remind me to buy milk" / "I need to buy milk" | Adds a task |
| "Add submit the report tomorrow with high priority" | Adds a high priority task due tomorrow |
| "Show my tasks" / "Read my to-do list" | Lists every task |
| "What's pending" / "Show completed tasks" | Lists only pending or only completed tasks |
| "Mark task two as done" / "I finished buy milk" | Completes a task by number or by name |
| "Delete task one" / "Remove the last task" | Deletes a task |
| "Clear completed tasks" | Removes all completed tasks |
| "Clear all tasks" | Empties the list |
| "Help" | Reads out the commands |
| "Exit" / "Goodbye" | Closes the app |

## Example session

```
Listening...
Heard: add buy milk
Added task 1: buy milk.

Listening...
Heard: remind me to submit the report tomorrow with high priority
Added task 2: submit the report (high priority, due tomorrow).

Listening...
Heard: mark task one as done
Marked task 1 as done: buy milk.

Listening...
Heard: show my tasks
You have 1 pending task.
1. [x] buy milk
2. [ ] submit the report (high priority, due tomorrow)
```

## Project structure

```
voice-todo-manager/
├── main.py              # command line entry point (voice / text / file modes)
├── voice_todo/
│   ├── speech.py        # microphone input and text-to-speech
│   ├── parser.py        # sentence -> command (rule based)
│   ├── app.py           # runs commands and builds replies
│   └── store.py         # task list saved as JSON
├── tests/               # unit tests for the parser and the command flow
└── requirements.txt
```

## How it works

1. `speech.py` records a phrase from the microphone and sends it to the Google Web Speech API, which returns text.
2. `parser.py` cleans the text and matches it against command patterns to produce a `Command` (action, task text, task number, priority, due date).
3. `app.py` applies the command to the task list and builds a reply.
4. `store.py` saves the list to `tasks.json`.
5. The reply is printed and spoken with `pyttsx3`.

## Running the tests

The tests need no microphone and no extra packages:

```bash
python -m unittest discover -s tests -t .
```

## Limitations

- Voice mode needs an internet connection (Google Web Speech API).
- English commands only.
- Due dates understand "today" and "tomorrow" only.
