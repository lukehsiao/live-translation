from __future__ import division

import sys
from enum import Enum
import time
import itertools
from textwrap import TextWrapper

from google.cloud import mediatranslation as media
import typer

from live_translation.microphone import MicrophoneStream

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
SpeechEventType = media.StreamingTranslateSpeechResponse.SpeechEventType

app = typer.Typer()


def _listen_print_loop(tw, output, responses):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.
    """
    translation = ""
    is_final = False
    for response in responses:
        # Once the transcription settles, the response contains the
        # END_OF_SINGLE_UTTERANCE event.
        if (
            is_final
            or response.speech_event_type == SpeechEventType.END_OF_SINGLE_UTTERANCE
        ):

            for line in tw.wrap(f"{translation}"):
                output.write(f"{line}\n")
                time.sleep(1)
            return 0

        result = response.result
        translation = result.text_translation_result.translation
        is_final = result.text_translation_result.is_final

        #  print(u"{0}".format(translation), end='\r')


def _do_translation_loop(tw: TextWrapper, source: str, target: str, outfile):
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

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        mic_requests = (
            media.StreamingTranslateSpeechRequest(audio_content=content)
            for content in audio_generator
        )

        requests = itertools.chain(iter([first_request]), mic_requests)

        responses = client.streaming_translate_speech(requests)

        # Print the translation responses as they arrive
        result = _listen_print_loop(tw, outfile, responses)
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
        50,
        "-w",
        "--width",
        help="The maximum length of lines in the caption file.",
        show_default=True,
    ),
):
    """
    Translate speech in one language to text in another using Google's Media
    Translation API.
    """

    typer.echo(
        f'Translating "{source_lang}" speech to "{target_lang}" text in ./{outfile} wrapped at {text_width} chars.'
    )

    while True:
        option = input("Press any key to start or 'q' to quit: ")

        if option.lower() == "q":
            break

        print("Press Ctrl+C to quit when finished.\nBegin speaking...", file=sys.stderr)

        tw = TextWrapper(width=text_width)

        with open(outfile, "w", buffering=1) as outfile:
            while True:
                _do_translation_loop(tw, source_lang, target_lang, outfile)


if __name__ == "__main__":
    typer.run(main)
