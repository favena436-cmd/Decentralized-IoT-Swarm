# Voice Pipeline Architecture \u2014 Swarm Collaboration

> Created: 2026-06-26
> Status: Operational
> Agents: OWL (Hermes), Antigravity Architect

## Goal

Native STT (Speech-to-Text) and TTS (Text-to-Speech) for all swarm agents, enabling:
- Voice conversation between Jimmy and any agent
- Phone-to-agent voice routing (Samsung S24 as input node)
- Agent-to-agent voice communication (future)

## Architecture

```
[Jimmy speaks] \u2192 [Microphone / Phone]
        \u2193
  [STT: Gemini 2.5 Flash]  \u2014 streaming transcription
        \u2193
  [LLM: Gemini 2.5 Flash]  \u2014 streaming response
        \u2193
  [TTS: Gemini 2.5 Flash Preview TTS]  \u2014 voice "Kore"
        \u2193
  [Speakers / Phone]
```

## File Structure

```
/home/jimmy/swarm_node/
\u251c\u2500\u2500 stt.py              # Standalone Speech-to-Text tool
\u251c\u2500\u2500 tts.py              # Standalone Text-to-Speech tool
\u251c\u2500\u2500 voice_chat.py       # Full voice-to-voice pipeline (STT \u2192 LLM \u2193 TTS)
\u2514\u2500\u2500 shared/
    \u2514\u2500\u2500 knowledge/
        \u2514\u2500\u2500 voice-pipeline.md  # This file
```

## Component Details

### stt.py \u2014 Speech-to-Text

**Purpose:** Records audio from microphone and transcribes using Gemini API.

**Usage:**
```bash
python3 stt.py                           # Record 5s, print transcript
python3 stt.py --duration 10              # Record 10s
python3 stt.py --quiet                    # Only output transcript
python3 stt.py --output transcript.txt    # Save to file
python3 stt.py --model gemini-2.5-flash  # Specify model
```

**Features:**
- Configurable recording duration (1-300s)
- Silence/timestamp artifact rejection (ignores "00:00", "[1:23]", etc.)
- Robust empty-parts handling for Gemini responses
- Graceful error handling (mic not found, API errors, timeouts)
- Quiet mode for piping/scripting

**Dependencies:** requests, arecord (ALSA)

### tts.py \u2014 Text-to-Speech

**Purpose:** Synthesizes text to speech using Gemini TTS API and plays via PulseAudio.

**Usage:**
```bash
python3 tts.py --text "Hello Jimmy"          # Speak text aloud
python3 tts.py --text "Hi" --voice Charon    # Use specific voice
python3 tts.py --text "Hi" --output hi.pcm   # Save PCM to file
python3 tts.py --text "Hi" --quiet            # No status messages
python3 tts.py --text "Hi" --no-play          # Synthesize but don't play
echo "Hello" | python3 tts.py               # Read from stdin
```

**Available Voices:** Kore, Charon, Puck, Fenrir, Aoede, Umbriel, Schedius, Rhea, Orpheus, Athena

**Features:**
- Multiple voice support
- Saves to raw PCM file option
- Plays via paplay (PulseAudio)
- Quiet mode for scripting
- stdin or CLI text input

**Dependencies:** google-genai SDK, paplay (PulseAudio)

### voice_chat.py \u2014 Full Voice-to-Voice Pipeline

**Purpose:** Complete voice conversation loop: Record \u2192 STT \u2192 LLM \u2192 TTS \u2192 Play

**Usage:**
```bash
python3 voice_chat.py                     # Single exchange
python3 voice_chat.py --continuous         # Continuous conversation loop
python3 voice_chat.py --quiet              # Minimal output
python3 voice_chat.py --voice Charon       # Use specific TTS voice
python3 voice_chat.py --duration 10        # Record for 10s
python3 voice_chat.py --clear-history      # Start fresh conversation
```

**Features:**
- Continuous conversation mode (--continuous)
- Conversation memory (saved to /tmp/swarm_voice_conversation.json)
- Configurable STT, LLM, and TTS models
- All capabilities of stt.py and tts.py combined
- Graceful Ctrl+C handling

**Dependencies:** requests, google-genai SDK, arecord, paplay

## Agent Responsibilities

### OWL (Hermes) \u2014 Voice Orchestrator
- File: `/home/jimmy/hermes_voice_chat.py`
- Role: Continuous conversation daemon with VAD
- Handles: VAD detection, streaming STT, streaming TTS, conversation memory

### Antigravity Architect \u2014 Chat Agent Voice Integration
- File: `/home/jimmy/teamwork_projects/xbox_ai_agent/chat_agent.py`
- Role: Code review + architecture design for voice pipeline
- Handles: google-genai SDK integration, tool calling, code execution

### Chat Node \u2014 User-Facing Voice I/O
- File: `/home/jimmy/teamwork_projects/xbox_ai_agent/host.py`
- Role: Push-to-talk voice interface to the Swarm
- Handles: Recording, STT via Gemini, routing to Chat Agent, TTS playback

### Xbox Hermes \u2014 Hardware Voice Node
- Role: Phone microphone input, screen casting, hardware I/O
- Status: Samsung S24 ADB connection needed (re-pair)

## Shared Components

| Component | Location | Status |
|-----------|----------|--------|
| STT (transcribe) | stt.py / Gemini 2.5 Flash REST API | \u2705 Working |
| TTS (speak) | tts.py / Gemini 2.5 Flash Preview TTS | \u2705 Working |
| Voice Chat | voice_chat.py / Full pipeline | \u2705 Working |
| VAD (voice detection) | webrtcvad + pyaudio | \u2705 Working |
| Conversation memory | /tmp/swarm_voice_conversation.json | \u2705 Working |
| Swarm protocol | swarm_node.py TCP JSON | \u2705 Working |
| Phone input | Samsung S24 ADB WiFi | \u274c Disconnected |

## How Agents Collaborate

1. **Jimmy speaks** \u2192 OWL's voice chat picks up via VAD
2. **OWL transcribes** \u2192 Gemini STT
3. **OWL routes** \u2192 If complex reasoning needed, sends to Antigravity via google-genai SDK
4. **Antigravity responds** \u2192 Code review, architecture, critique
5. **OWL speaks back** \u2192 Gemini TTS to speakers

## Quick Start

```bash
# Test TTS (should play audio):
python3 /home/jimmy/swarm_node/tts.py --text "Hello Jimmy" --quiet

# Test STT (record 3s, print transcript):
python3 /home/jimmy/swarm_node/stt.py --duration 3 --quiet

# Full voice chat (single exchange):
python3 /home/jimmy/swarm_node/voice_chat.py --quiet

# Continuous conversation:
python3 /home/jimmy/swarm_node/voice_chat.py --continuous
```

## Next Steps

- [ ] Test chat_agent.py interactively (Antigravity)
- [ ] Reconnect Samsung S24 via ADB
- [ ] Create desktop launcher for voice chat
- [ ] Agent-to-agent voice routing (future)

---
Maintained by: OWL (Hermes) & Antigravity Architect
