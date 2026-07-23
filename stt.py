#!/usr/bin/env python3
"""
stt.py — Standalone speech-to-text tool for any agent.

Records audio from the microphone, sends it to Gemini for transcription,
and prints the transcribed text to stdout.

Usage:
  python3 stt.py                     # Record 5s, print transcript
  python3 stt.py --duration 10        # Record 10s
  python3 stt.py --quiet              # Only output transcript (no status msgs)
  python3 stt.py --output file.txt    # Save transcript to file
  python3 stt.py --model gemini-2.5-flash  # Specify model

Dependencies: Python 3 stdlib + requests + arecord (ALSA)
"""
import os
import re
import sys
import argparse
import subprocess
import tempfile
import base64

# Configuration
DEFAULT_DURATION = 5
DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
API_KEY_PATH=os.environ["HOME"] + "/.gemini_api_key"

# Patterns that indicate silence/noise artifacts rather than real speech
SILENCE_PATTERNS = [
    re.compile(r"^\d{1,2}:\d{2}\s*$"),          # "00:00", "1:23"
    re.compile(r"^\d{1,2}:\d{2}:\d{2}\s*$"),     # "00:00:00", "1:23:45"
    re.compile(r"^\[\d{1,2}:\d{2}\]\s*$"),      # "[00:00]"
    re.compile(r"^\(\d{1,2}:\d{2}\)\s*$"),      # "(00:00)"
    re.compile(r"^[\s\-\.]*$"),                    # Only whitespace/dashes/dots
    re.compile(r"^(um+|uh+|ah+|er+)\s*$", re.IGNORECASE),  # Filler sounds only
    re.compile(r"^(music|silence|noise|static)\s*$", re.IGNORECASE),  # Labels
]


def is_silence_artifact(text):
    """Check if transcript is just a silence/timestamp artifact, not real speech."""
    if not text:
        return True
    text = text.strip()
    if len(text) < 3:
        # Very short responses are likely artifacts unless they are meaningful words
        meaningful_short = {"yes", "no", "hi", "ok", "hey", "bye", "yo", "hmm"}
        if text.lower() not in meaningful_short:
            return True
    for pattern in SILENCE_PATTERNS:
        if pattern.match(text):
            return True
    return False


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


def record_audio(duration, quiet=False):
    """Record audio from the default microphone for `duration` seconds.

    Returns the path to the WAV file, or None on failure.
    """
    wav_file = tempfile.mktemp(suffix=".wav")
    cmd = [
        "arecord",
        "-D", "default",
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "2",
        "-d", str(duration),
        wav_file,
    ]
    try:
        if not quiet:
            print(f"Recording for {duration}s...", end="", flush=True)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=duration + 5,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            if "cannot open" in stderr.lower() or "device" in stderr.lower():
                print(f"\nError: Microphone not available — {stderr}", file=sys.stderr)
            else:
                print(f"\nError: Recording failed — {stderr}", file=sys.stderr)
            try:
                os.unlink(wav_file)
            except OSError:
                pass
            return None
    except FileNotFoundError:
        print("Error: 'arecord' not found. Install ALSA utilities (alsa-utils).", file=sys.stderr)
        try:
            os.unlink(wav_file)
        except OSError:
            pass
        return None
    except subprocess.TimeoutExpired:
        print("\nError: Recording timed out.", file=sys.stderr)
        try:
            os.unlink(wav_file)
        except OSError:
            pass
        return None

    if not quiet:
        print(" done.")

    # Verify the file has actual audio data (header is 44 bytes)
    try:
        size = os.path.getsize(wav_file)
        if size < 100:
            print("Error: Recorded audio file is too small — no mic input detected.", file=sys.stderr)
            try:
                os.unlink(wav_file)
            except OSError:
                pass
            return None
    except OSError:
        return None

    return wav_file


def transcribe(audio_path, api_key, model=DEFAULT_MODEL, quiet=False):
    """Send audio to Gemini and return the transcribed text."""
    import requests

    try:
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    except OSError as e:
        print(f"Error: Cannot read audio file — {e}", file=sys.stderr)
        return ""

    if not quiet:
        print("Transcribing...", end="", flush=True)

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                {"text": "You are a speech-to-text transcription assistant. Transcribe any speech you hear in the audio. If you hear speech, output ONLY the transcribed words. If there is no speech or only silence/noise in the audio, output nothing. Do not add any commentary, labels, or explanations. Do not output timestamps."}
            ]
        }]
    }

    try:
        resp = requests.post(
            f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}",
            json=payload,
            timeout=30,
        )
    except requests.exceptions.Timeout:
        if not quiet:
            print()
        print("Error: API request timed out.", file=sys.stderr)
        return ""
    except requests.exceptions.ConnectionError:
        if not quiet:
            print()
        print("Error: Cannot connect to Gemini API — check your internet connection.", file=sys.stderr)
        return ""
    except requests.exceptions.RequestException as e:
        if not quiet:
            print()
        print(f"Error: API request failed — {e}", file=sys.stderr)
        return ""

    if resp.status_code != 200:
        try:
            err_data = resp.json()
            err_msg = err_data.get("error", {}).get("message", resp.text[:200])
        except ValueError:
            err_msg = resp.text[:200]
        print(f"Error: API returned {resp.status_code} — {err_msg}", file=sys.stderr)
        return ""

    try:
        data = resp.json()
    except ValueError:
        if not quiet:
            print()
        print("Error: Invalid JSON response from API.", file=sys.stderr)
        return ""

    # Extract text from response, handling empty/missing parts
    text = ""
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            # Check for prompt feedback (safety blocks, etc.)
            block_reason = data.get("promptFeedback", {}).get("blockReason", "")
            if block_reason:
                print(f"Error: Request blocked — {block_reason}", file=sys.stderr)
            return ""

        content_obj = candidates[0].get("content", {})
        parts = content_obj.get("parts", [])

        if not parts:
            # Empty parts — no speech detected
            return ""

        # Collect text from all parts
        text_parts = []
        for part in parts:
            txt = part.get("text", "")
            if txt:
                text_parts.append(txt)

        text = " ".join(text_parts).strip()

    except (KeyError, IndexError, AttributeError) as e:
        if not quiet:
            print()
        print(f"Error: Unexpected response structure — {e}", file=sys.stderr)
        return ""

    if not quiet:
        sys.stdout.flush()
        print(" done.")
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Record audio and transcribe using Gemini STT."
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=DEFAULT_DURATION,
        help=f"Recording duration in seconds (default: {DEFAULT_DURATION})",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save transcript to FILE instead of stdout",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Gemini model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress status messages; only output transcript",
    )
    args = parser.parse_args()

    # Validate API key
    api_key = get_api_key()
    if not api_key:
        print("Error: No Gemini API key found. Set GEMINI_API_KEY env var or create ~/.gemini_api_key", file=sys.stderr)
        sys.exit(1)

    # Validate duration
    if args.duration < 1:
        print("Error: Duration must be at least 1 second.", file=sys.stderr)
        sys.exit(1)
    if args.duration > 300:
        print("Error: Duration cannot exceed 300 seconds.", file=sys.stderr)
        sys.exit(1)

    # Record audio
    wav_file = record_audio(args.duration, quiet=args.quiet)
    if wav_file is None:
        sys.exit(1)

    try:
        # Transcribe
        transcript = transcribe(wav_file, api_key, model=args.model, quiet=args.quiet)

        # Clean up temp file
        try:
            os.unlink(wav_file)
        except OSError:
            pass

        # Handle empty transcript or silence artifacts
        if not transcript or is_silence_artifact(transcript):
            if not args.quiet:
                sys.stdout.flush()
                print("(no speech detected)", file=sys.stderr)
            sys.exit(0)

        # Output result
        if args.output:
            try:
                with open(args.output, "w") as f:
                    f.write(transcript + "\n")
                if not args.quiet:
                    print(f"Transcript saved to {args.output}")
            except OSError as e:
                print(f"Error: Cannot write to {args.output} — {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(transcript)

    except KeyboardInterrupt:
        # Clean up on Ctrl+C
        try:
            os.unlink(wav_file)
        except OSError:
            pass
        if not args.quiet:
            print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
