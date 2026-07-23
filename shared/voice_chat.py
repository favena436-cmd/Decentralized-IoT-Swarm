#!/usr/bin/env python3
"""
voice_chat.py \u2014 Full voice-to-voice pipeline for swarm agents.

Records speech, transcribes via Gemini STT, gets an LLM response,
synthesizes via Gemini TTS, and plays the result.

Usage:
  python3 voice_chat.py                  # Single voice exchange
  python3 voice_chat.py --continuous      # Continuous conversation loop
  python3 voice_chat.py --quiet           # Minimal output
  python3 voice_chat.py --voice Charon     # Use specific TTS voice

Dependencies: Python 3 stdlib + google-genai SDK + requests + arecord + paplay
"""
import os
import sys
import argparse
import subprocess
import tempfile
import base64
import re
import json
from datetime import datetime

# Configuration
DEFAULT_STT_MODEL = "gemini-2.5-flash"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_TTS_VOICE = "Kore"
DEFAULT_LLM_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
API_KEY_PATH=os.environ["HOME"] + "/.gemini_api_key"
CONVERSATION_MEMORY_PATH = "/tmp/swarm_voice_conversation.json"

# Silence artifact patterns (same as stt.py)
SILENCE_PATTERNS = [
    re.compile(r"^\d{1,2}:\d{2}\s*$"),
    re.compile(r"^\d{1,2}:\d{2}:\d{2}\s*$"),
    re.compile(r"^[\s\-\.]*$"),
    re.compile(r"^(music|silence|noise|static)\s*$", re.IGNORECASE),
]


def get_api_key():
    """Retrieve Gemini API key from env or file."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    if os.path.exists(API_KEY_PATH):
        try:
            key = open(API_KEY_PATH).read().strip()
            if key:
                return key
        except OSError:
            pass
    return ""


def is_silence_artifact(text):
    """Check if transcript is just a silence/timestamp artifact."""
    if not text:
        return True
    text = text.strip()
    if len(text) < 3:
        meaningful_short = {"yes", "no", "hi", "ok", "hey", "bye", "yo", "hmm"}
        if text.lower() not in meaningful_short:
            return True
    for pattern in SILENCE_PATTERNS:
        if pattern.match(text):
            return True
    return False


def record_audio(duration, quiet=False):
    """Record audio from the default microphone."""
    wav_file = tempfile.mktemp(suffix=".wav")
    cmd = [
        "arecord", "-D", "default", "-f", "S16_LE",
        "-r", "16000", "-c", "2", "-d", str(duration), wav_file,
    ]
    try:
        if not quiet:
            print(f"\U0001f3a4 Recording for {duration}s...", end="", flush=True)
        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=duration + 5,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            print(f"\nError: Recording failed \u2014 {stderr}", file=sys.stderr)
            try: os.unlink(wav_file)
            except OSError: pass
            return None
    except FileNotFoundError:
        print("Error: arecord not found. Install alsa-utils.", file=sys.stderr)
        try: os.unlink(wav_file)
        except OSError: pass
        return None
    except subprocess.TimeoutExpired:
        print("\nError: Recording timed out.", file=sys.stderr)
        try: os.unlink(wav_file)
        except OSError: pass
        return None

    if not quiet:
        print(" done.")

    try:
        size = os.path.getsize(wav_file)
        if size < 100:
            print("Error: Audio file too small.", file=sys.stderr)
            try: os.unlink(wav_file)
            except OSError: pass
            return None
    except OSError:
        return None

    return wav_file


def transcribe(audio_path, api_key, model=DEFAULT_STT_MODEL, quiet=False):
    """Send audio to Gemini STT and return transcribed text."""
    import requests

    try:
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    except OSError as e:
        print(f"Error: Cannot read audio \u2014 {e}", file=sys.stderr)
        return ""

    if not quiet:
        print("\U0001f4dd Transcribing...", end="", flush=True)

    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
            {"text": "Transcribe the speech in this audio. Output ONLY the transcribed words, nothing else. If no speech, output nothing."}
        ]}]
    }

    try:
        resp = requests.post(
            f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}",
            json=payload, timeout=30,
        )
    except requests.exceptions.RequestException as e:
        if not quiet: print()
        print(f"Error: STT API failed \u2014 {e}", file=sys.stderr)
        return ""

    if resp.status_code != 200:
        print(f"Error: STT returned {resp.status_code}", file=sys.stderr)
        return ""

    try:
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if p.get("text")]
        text = " ".join(text_parts).strip()
    except (ValueError, KeyError, IndexError) as e:
        print(f"Error: Bad response \u2014 {e}", file=sys.stderr)
        return ""

    if not quiet:
        sys.stdout.flush()
        print(" done.")
    return text


def get_llm_response(prompt, api_key, conversation_history=None, model=DEFAULT_LLM_MODEL, quiet=False):
    """Send prompt to Gemini LLM and return the response text."""
    from google import genai
    from google.genai import types

    if not quiet:
        print("\U0001f916 Thinking...", end="", flush=True)

    client = genai.Client(api_key=api_key)

    # Build system instruction with conversation context
    system_prompt = "You are a helpful voice assistant in a swarm AI system. Keep responses concise and conversational. Answer in 1-3 sentences unless more detail is clearly needed."
    if conversation_history:
        # Include last few exchanges for context
        context_lines = []
        for exchange in conversation_history[-6:]:
            role = exchange.get("role", "user")
            content = exchange.get("content", "")
            context_lines.append(f"{role}: {content}")
        if context_lines:
            system_prompt += "\n\nRecent conversation:\n" + "\n".join(context_lines)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=512,
                temperature=0.7,
            )
        )
    except Exception as e:
        if not quiet: print()
        print(f"Error: LLM request failed \u2014 {e}", file=sys.stderr)
        return ""

    try:
        text = response.text.strip()
    except (AttributeError, IndexError):
        if not quiet: print()
        print("Error: No text in LLM response.", file=sys.stderr)
        return ""

    if not quiet:
        sys.stdout.flush()
        print(" done.")
    return text


def synthesize_tts(text, api_key, voice=DEFAULT_TTS_VOICE, model=DEFAULT_TTS_MODEL, quiet=False):
    """Synthesize text to PCM audio via Gemini TTS."""
    from google import genai
    from google.genai import types

    if not quiet:
        print(f"\U0001f50a Speaking ({voice})...", end="", flush=True)

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
    except Exception as e:
        if not quiet: print()
        print(f"Error: TTS failed \u2014 {e}", file=sys.stderr)
        return None

    try:
        audio_data = response.candidates[0].content.parts[0].inline_data.data
    except (IndexError, AttributeError):
        if not quiet: print()
        print("Error: No audio in TTS response.", file=sys.stderr)
        return None

    if not audio_data:
        if not quiet: print()
        print("Error: Empty audio from TTS.", file=sys.stderr)
        return None

    if not quiet:
        print(" done.")
    return audio_data


def play_pcm(audio_data):
    """Play raw PCM audio through paplay."""
    pcm_file = tempfile.mktemp(suffix=".pcm")
    try:
        with open(pcm_file, "wb") as f:
            f.write(audio_data)
    except OSError as e:
        print(f"Error: Cannot write PCM \u2014 {e}", file=sys.stderr)
        return False

    try:
        cmd = ["paplay", "--rate", "24000", "--channels", "1",
               "--format", "s16le", "--raw", pcm_file]
        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=max(30, len(audio_data) // (24000 * 1 * 2) + 5),
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            print(f"Error: Playback failed \u2014 {stderr}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print("Error: paplay not found.", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("Error: Playback timed out.", file=sys.stderr)
        return False
    finally:
        try: os.unlink(pcm_file)
        except OSError: pass


def load_conversation():
    """Load conversation history from disk."""
    if os.path.exists(CONVERSATION_MEMORY_PATH):
        try:
            with open(CONVERSATION_MEMORY_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_conversation(history):
    """Save conversation history to disk."""
    try:
        with open(CONVERSATION_MEMORY_PATH, "w") as f:
            json.dump(history[-50:], f, indent=2)  # Keep last 50 exchanges
    except OSError:
        pass


def voice_exchange(api_key, args):
    """Perform one voice exchange: record \u2192 STT \u2192 LLM \u2192 TTS \u2192 play."""
    # Step 1: Record
    wav_file = record_audio(args.duration, quiet=args.quiet)
    if wav_file is None:
        return None

    try:
        # Step 2: Transcribe
        transcript = transcribe(wav_file, api_key, model=args.stt_model, quiet=args.quiet)
        try: os.unlink(wav_file)
        except OSError: pass

        if not transcript or is_silence_artifact(transcript):
            if not args.quiet:
                print("(no speech detected)", file=sys.stderr)
            return None

        if not args.quiet:
            print(f"\nYou: {transcript}")
        else:
            print(f"You: {transcript}")

        # Step 3: Get LLM response
        history = load_conversation()
        response = get_llm_response(
            transcript, api_key,
            conversation_history=history,
            model=args.llm_model,
            quiet=args.quiet,
        )

        if not response:
            if not args.quiet:
                print("(no response from LLM)", file=sys.stderr)
            return None

        if not args.quiet:
            print(f"Agent: {response}")
        else:
            print(f"Agent: {response}")

        # Step 4: TTS synthesis + playback
        audio_data = synthesize_tts(
            response, api_key,
            voice=args.voice,
            model=args.tts_model,
            quiet=args.quiet,
        )

        if audio_data is None:
            if not args.quiet:
                print("(TTS failed)", file=sys.stderr)
            return None

        success = play_pcm(audio_data)
        if not success and not args.quiet:
            print("(playback failed)", file=sys.stderr)

        # Save to conversation history
        history.append({"role": "user", "content": transcript})
        history.append({"role": "assistant", "content": response})
        save_conversation(history)

        return response

    except KeyboardInterrupt:
        try: os.unlink(wav_file)
        except OSError: pass
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Voice-to-voice pipeline: STT \u2192 LLM \u2192 TTS"
    )
    parser.add_argument("--duration", "-d", type=int, default=5,
                        help="Recording duration in seconds (default: 5)")
    parser.add_argument("--voice", "-v", type=str, default=DEFAULT_TTS_VOICE,
                        help=f"TTS voice (default: {DEFAULT_TTS_VOICE})")
    parser.add_argument("--stt-model", type=str, default=DEFAULT_STT_MODEL,
                        help=f"STT model (default: {DEFAULT_STT_MODEL})")
    parser.add_argument("--tts-model", type=str, default=DEFAULT_TTS_MODEL,
                        help=f"TTS model (default: {DEFAULT_TTS_MODEL})")
    parser.add_argument("--llm-model", type=str, default=DEFAULT_LLM_MODEL,
                        help=f"LLM model (default: {DEFAULT_LLM_MODEL})")
    parser.add_argument("--continuous", "-c", action="store_true",
                        help="Run in continuous conversation mode")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Minimal output")
    parser.add_argument("--clear-history", action="store_true",
                        help="Clear conversation history on startup")
    args = parser.parse_args()

    # Validate API key
    api_key = get_api_key()
    if not api_key:
        print("Error: No Gemini API key found.", file=sys.stderr)
        sys.exit(1)

    # Clear history if requested
    if args.clear_history:
        save_conversation([])
        if not args.quiet:
            print("Conversation history cleared.")

    if not args.quiet:
        print("=" * 50)
        print("\U0001f3a4 Swarm Voice Chat")
        print(f"  STT: {args.stt_model}")
        print(f"  LLM: {args.llm_model}")
        print(f"  TTS: {args.tts_model} (voice: {args.voice})")
        print(f"  Duration: {args.duration}s")
        print("=" * 50)
        if args.continuous:
            print("\nContinuous mode. Press Ctrl+C to stop.\n")
        else:
            print("\nSpeak after the prompt. Press Ctrl+C to exit.\n")

    try:
        if args.continuous:
            while True:
                try:
                    result = voice_exchange(api_key, args)
                    if result is None:
                        # No speech detected, retry
                        continue
                except KeyboardInterrupt:
                    if not args.quiet:
                        print("\n\nGoodbye! \U0001f44b")
                    break
        else:
            try:
                voice_exchange(api_key, args)
            except KeyboardInterrupt:
                if not args.quiet:
                    print("\n\nInterrupted.")
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\nGoodbye! \U0001f44b")

    sys.exit(0)


if __name__ == "__main__":
    main()
