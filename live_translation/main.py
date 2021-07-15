from __future__ import division

from ctypes import *
from contextlib import contextmanager
import itertools

from google.cloud import mediatranslation as media
import pyaudio
from six.moves import queue

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
SpeechEventType = media.StreamingTranslateSpeechResponse.SpeechEventType

# To suppress pyaudio warnings
# See: https://stackoverflow.com/a/17673011
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)


@contextmanager
def noalsaerr():
    asound = cdll.LoadLibrary("libasound.so")
    asound.snd_lib_error_set_handler(c_error_handler)
    yield
    asound.snd_lib_error_set_handler(None)


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        with noalsaerr():
            self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type=None, value=None, traceback=None):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def exit(self):
        self.__exit__()

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


def listen_print_loop(responses):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.
    """
    translation = ""
    for response in responses:
        # Once the transcription settles, the response contains the
        # END_OF_SINGLE_UTTERANCE event.
        if response.speech_event_type == SpeechEventType.END_OF_SINGLE_UTTERANCE:

            print(u"\nFinal translation: {0}".format(translation))
            return 0

        result = response.result
        translation = result.text_translation_result.translation

        #  print(u'\nPartial translation: {0}'.format(translation))


def do_translation_loop():

    client = media.SpeechTranslationServiceClient()

    speech_config = media.TranslateSpeechConfig(
        audio_encoding="linear16",
        source_language_code="en-US",
        target_language_code="es-MX",
    )

    config = media.StreamingTranslateSpeechConfig(
        audio_config=speech_config, single_utterance=True
    )

    # The first request contains the configuration.
    # Note that audio_content is explicitly set to None.
    first_request = media.StreamingTranslateSpeechRequest(
        streaming_config=config, audio_content=None
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        mic_requests = (
            media.StreamingTranslateSpeechRequest(
                audio_content=content, streaming_config=config
            )
            for content in audio_generator
        )

        requests = itertools.chain(iter([first_request]), mic_requests)

        responses = client.streaming_translate_speech(requests)

        # Print the translation responses as they arrive
        result = listen_print_loop(responses)
        if result == 0:
            stream.exit()


def main():
    while True:
        print()
        option = input("Press any key to translate or 'q' to quit: ")

        if option.lower() == "q":
            break

        print("Begin speaking...")

        do_translation_loop()


if __name__ == "__main__":
    main()
