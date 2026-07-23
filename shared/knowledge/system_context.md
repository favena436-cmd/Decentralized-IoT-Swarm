# Agent Knowledge Base

## System Context
- Host: Jimmy's HP Laptop (Ubuntu 24.04, Python 3.12, 6.17 kernel)
- Swarm Node: /home/jimmy/swarm_node.py (TCP socket server, JSON protocol)
- Hermes Agent: active with git safety hooks (pre-commit, pre-push)
- Git config: rebase=true, merge.conflictstyle=diff3, LFS configured

## Projects

### Dictate
- Location: /home/jimmy/dictate/
- Global dictation utility (STT + punctuation + text injection)
- Modules: dictate.py, overlay.py, hotkey_listener.py, tray.py, deploy.sh
- Config: ~/.config/dictate/config.json
- Venv: ~/.venv-dictate
- Dependencies: xdotool, xclip, python3-tk, pynput
- Overlays: Neon Pulse, Breathing Wave, Electric Spark
- States: recording/thinking/processing/typing

### Voice Assistant (standalone)
- Location: /home/jimmy/voice_assistant.py
- Uses Gemini API for intelligent responses
- STT via SpeechRecognition (Google free), TTS via pyttsx3
- Requirements: SpeechRecognition, pyttsx3, PyAudio, requests
- API key: ~/.gemini_api_key

### Voice Assistant Frontend (teamwork)
- Location: /home/jimmy/teamwork_projects/voice_assistant_frontend/
- Low-latency stateful voice assistant with interruption support
- src/: frontend_service.py, backend_simulator.py, overlay_gui.py
- tests/: run_tests.py, audio_generator.py
- Protocol: STT on port 5001, TTS on port 5002 (TCP sockets)
- Milestones 1-5 complete, Milestone 6 (E2E verification) in progress
- Architecture: Frontend captures audio → STT socket → Gemini → TTS socket → playback

### Xbox AI Agent
- Location: /home/jimmy/teamwork_projects/xbox_ai_agent/
- Status: early stage

## Common Commands
- Python: python3 --version (3.12)
- Install packages: pip3 install --break-system-packages <pkg>
- System packages: sudo apt install -y <pkg>
- Git safety hooks: active (blocks push to main, secrets, .env, conflict markers)
- Git aliases: st, co, sw, lg, undo, unstage, cleanup, quick
- Portaudio: sudo apt install -y portaudio19-dev (for PyAudio)

## Agent Filing Conventions
- Knowledge: shared/knowledge/ — long-term facts and references
- Tasks: shared/tasks/registry.json — active/completed task tracking
- Results: shared/results/ — completed task outputs
- Logs: shared/logs/ — agent activity logs
- Agent scratch: agents/<name>/ — per-agent working files
- Naming: YYYY-MM-DD_agent_topic.ext

## Environment Notes
- ALSA messages in terminal are normal (no JACK server, pipewire present)
- 6 microphones available (including pipewire, default)
- 131 TTS voices available via espeak-ng
- Memory limit: 2200 chars (keep entries compact)
