# -*- coding: utf-8 -*-

# Copyright 2020 Google LLC
# Modifications copyright 2021 Luke Hsiao
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import division

import itertools
import queue
import sys
import time
from collections import deque
from textwrap import TextWrapper

import typer
from google.cloud import mediatranslation as media
from pynput import keyboard

from live_translation.microphone import MicrophoneStream

# Audio recording parameters
SpeechEventType = media.StreamingTranslateSpeechResponse.SpeechEventType

app = typer.Typer()

# Thread-safe, unbounded FIFO queue for passing keyboard events
q = queue.SimpleQueue()

SWAP = "s"


def _on_press(key):
    #  try:
    #      print(f"key: {key.char} pressed")
    #  except AttributeError:
    #      print(f"special key: {key} pressed")
    pass


def _on_release(key):
    try:
        if key.char == SWAP:
            q.put(SWAP)
    except AttributeError:
        pass

    if key == keyboard.Key.esc:
        q.put(key)
        # Stop the listener
        return False


def _listen_print_loop(tw, output, responses, text_buffer):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.
    """
    translation = ""
    is_final = False
    max_len = 0
    for response in responses:
        # Once the transcription settles, the response contains the
        # END_OF_SINGLE_UTTERANCE event.
        if (
            is_final
            or response.speech_event_type == SpeechEventType.END_OF_SINGLE_UTTERANCE
        ):
            text_buffer.extend(translation.strip() + " ")
            fill = "~^~".join(tw.wrap(f"{''.join(text_buffer)}"))
            output.write(f"{fill}\n")

            # Give a brief pause at the end of an utterance
            time.sleep(0.3)
            return 0

        result = response.result
        translation = result.text_translation_result.translation
        max_len = max(max_len, len(translation))

        # Make room on the right for the next utterance
        while len(text_buffer) + max_len >= text_buffer.maxlen:
            text_buffer.popleft()

        # Keep clearing until the word boundary
        while len(text_buffer) and text_buffer[0] != " ":
            text_buffer.popleft()

        is_final = result.text_translation_result.is_final

        text_buffer.extend(translation.strip())
        fill = "~^~".join(tw.wrap(f"{''.join(text_buffer)}"))
        output.write(f"{fill}\n")

        # Undo in-progress translation
        for _ in range(len(translation)):
            text_buffer.pop()


def _do_translation_loop(
    tw: TextWrapper, source: str, target: str, outfile, text_buffer: deque
):
    client = media.SpeechTranslationServiceClient()

    speech_config = media.TranslateSpeechConfig(
        audio_encoding="linear16",
        source_language_code=source,
        target_language_code=target,
    )

    config = media.StreamingTranslateSpeechConfig(
        audio_config=speech_config, single_utterance=True
    )

    # The first request contains the configuration.
    # Note that audio_content is explicitly set to None.
    first_request = media.StreamingTranslateSpeechRequest(streaming_config=config)

    with MicrophoneStream() as stream:
        audio_generator = stream.generator()

        mic_requests = (
            media.StreamingTranslateSpeechRequest(audio_content=content)
            for content in audio_generator
        )

        requests = itertools.chain(iter([first_request]), mic_requests)

        responses = client.streaming_translate_speech(requests)

        # Print the translation responses as they arrive
        result = _listen_print_loop(tw, outfile, responses, text_buffer)
        if result == 0:
            stream.exit()


@app.command()
def main(
    source_lang: str = typer.Option(
        "en-US", "-f", "--source-lang", help="The speaker's language", show_default=True
    ),
    target_lang: str = typer.Option(
        "es-MX",
        "-t",
        "--target-lang",
        help="The language to translate captions to",
        show_default=True,
    ),
    outfile: str = typer.Option(
        "captions.txt",
        "-o",
        "--outfile",
        help="What to name the caption file.",
        show_default=True,
    ),
    text_width: int = typer.Option(
        55,
        "-w",
        "--width",
        help="The maximum length of lines in the caption file.",
        show_default=True,
    ),
):
    """
    Translate speech in one language to text in another using Google's Media
    Translation API.

    Press 's' to swap between source and target languages during runtime.
    """
    try:
        with open(outfile, "w", buffering=1) as outfile:

            while True:
                option = input("Press any key to start or 'q' to quit: ")

                if option.lower() == "q":
                    break

                tw = TextWrapper(width=text_width)

                # start keyboard listener in separate thread
                listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
                listener.start()

                l1 = source_lang
                l2 = target_lang
                print(
                    f"[INFO] Now translating from {l1} speech to {l2} text",
                    file=sys.stderr,
                )

                text_buffer = deque(maxlen=text_width * 3)
                while True:
                    # Check to see if we should toggle languages.
                    while not q.empty():
                        key = q.get()
                        if key == SWAP:
                            # Swap languages
                            l1, l2 = l2, l1
                            print(
                                f"[INFO] Now translating from {l1} speech to {l2} text",
                                file=sys.stderr,
                            )
                        elif key == keyboard.Key.esc:
                            return

                    _do_translation_loop(tw, l1, l2, outfile, text_buffer)
    except KeyboardInterrupt:
        print("Exiting!")


if __name__ == "__main__":
    typer.run(main)
