import asyncio
import edge_tts
import os
import time
import threading
from typing import Any

async def _generate_audio(text: str, output_path: str, voice: str = "en-IN-PrabhatNeural"):
    """Internal async function to generate energetic financial-news TTS."""
    # Fast pacing (+25% for 1.25x speed) and higher pitch (+5Hz) to sound exciting, like a real shorts creator.
    communicate = edge_tts.Communicate(text, voice, rate="+25%", pitch="+5Hz")
    await communicate.save(output_path)


def _run_coro(coro: Any):
    """Run a coroutine safely even if caller already has an active event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = {"value": None, "error": None}

    def _runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:  # pragma: no cover
            result["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if result["error"] is not None:
        raise result["error"]
    return result["value"]

def generate_audio_from_text(text: str, output_path: str, retries: int = 3):
    """Generates an energetic MP3 file from the given text using a fast Indian English voice."""
    if os.path.exists(output_path):
        os.remove(output_path)
        
    for attempt in range(retries):
        try:
            _run_coro(_generate_audio(text, output_path))
            return output_path
        except Exception as e:
            print(f"TTS Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                raise RuntimeError(f"Edge TTS API Failed after {retries} attempts: {e}")
            time.sleep(1.5)
