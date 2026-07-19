#!/usr/bin/env python3
"""
tts.py — Standalone text-to-speech tool for any agent.

Sends text to Gemini TTS API and plays the resulting audio through the
default PulseAudio output via paplay.

Usage:
  python3 tts.py --text "Hello Jimmy"          # Speak text
  python3 tts.py --text "Hello" --voice Charon  # Use specific voice
  python3 tts.py --text "Hello" --output hello.pcm  # Save PCM to file
  python3 tts.py --text "Hello" --quiet          # No status messages
  echo "Hello" | python3 tts.py                  # Read text from stdin
  python3 tts.py --text "Hi" --no-play           # Synthesize but don't play

Dependencies: Python 3 stdlib + google-genai SDK + paplay (PulseAudio)
"""
import os
import sys
import argparse
import subprocess
import tempfile

# Configuration
DEFAULT_VOICE = "Kore"
DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
API_KEY_PATH = os.path.join(os.path.expanduser("~"), ".gemini_api_key")
AUDIO_RATE = 24000
AUDIO_CHANNELS = 1
AUDIO_FORMAT = "s16le"

VOICES = [
    "Kore", "Charon", "Puck", "Fenrir", "Aoede",
    "Umbriel", "Schedius", "Rhea", "Orpheus", "Athena",
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


def synthesize(text, api_key, voice=DEFAULT_VOICE, model=DEFAULT_MODEL, quiet=False):
    """Send text to Gemini TTS API and return raw PCM audio bytes."""
    from google import genai
    from google.genai import types

    if not quiet:
        print(f"Synthesizing ({voice})...", end="", flush=True)

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )
        )
    except Exception as e:
        if not quiet:
            print()
        print(f"Error: TTS API request failed - {e}", file=sys.stderr)
        return None

    try:
        audio_data = response.candidates[0].content.parts[0].inline_data.data
    except (IndexError, AttributeError) as e:
        if not quiet:
            print()
        print(f"Error: No audio data in response - {e}", file=sys.stderr)
        try:
            block_reason = response.prompt_feedback.block_reason
            if block_reason:
                print(f"Blocked: {block_reason}", file=sys.stderr)
        except (AttributeError, KeyError):
            pass
        return None

    if not audio_data:
        if not quiet:
            print()
        print("Error: Empty audio response from API.", file=sys.stderr)
        return None

    if not quiet:
        print(" done.")
    return audio_data


def play_pcm(audio_data, quiet=False):
    """Play raw PCM audio data through paplay (PulseAudio)."""
    pcm_file = tempfile.mktemp(suffix=".pcm")
    try:
        with open(pcm_file, "wb") as f:
            f.write(audio_data)
    except OSError as e:
        print(f"Error: Cannot write temp audio file - {e}", file=sys.stderr)
        return False

    try:
        cmd = [
            "paplay",
            "--rate", str(AUDIO_RATE),
            "--channels", str(AUDIO_CHANNELS),
            "--format", AUDIO_FORMAT,
            "--raw",
            pcm_file,
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=max(30, len(audio_data) // (AUDIO_RATE * AUDIO_CHANNELS * 2) + 5),
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            print(f"Error: Audio playback failed - {stderr}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print("Error: paplay not found. Install PulseAudio utilities.", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("Error: Audio playback timed out.", file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(pcm_file)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Synthesize text to speech using Gemini TTS."
    )
    parser.add_argument("--text", "-t", type=str, default=None,
                        help="Text to synthesize (if omitted, reads from stdin)")
    parser.add_argument("--voice", "-v", type=str, default=DEFAULT_VOICE,
                        choices=VOICES, help=f"Voice to use (default: {DEFAULT_VOICE})")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL,
                        help=f"Gemini TTS model (default: {DEFAULT_MODEL})")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Save raw PCM audio to FILE")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress status messages")
    parser.add_argument("--no-play", action="store_true",
                        help="Don't play audio (just synthesize and optionally save)")
    args = parser.parse_args()

    if args.text:
        text = args.text
    else:
        if sys.stdin.isatty():
            print("Enter text to synthesize (Ctrl+D when done):", file=sys.stderr)
        text = sys.stdin.read().strip()

    if not text:
        print("Error: No text provided.", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        print("Error: No Gemini API key found.", file=sys.stderr)
        sys.exit(1)

    audio_data = synthesize(text, api_key, voice=args.voice, model=args.model, quiet=args.quiet)
    if audio_data is None:
        sys.exit(1)

    if args.output:
        try:
            with open(args.output, "wb") as f:
                f.write(audio_data)
            if not args.quiet:
                print(f"Audio saved to {args.output} ({len(audio_data)} bytes)")
        except OSError as e:
            print(f"Error: Cannot write to {args.output} - {e}", file=sys.stderr)
            sys.exit(1)

    if not args.no_play:
        success = play_pcm(audio_data, quiet=args.quiet)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
