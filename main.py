from slack_sdk import WebClient, RTMClient
from slack_sdk.errors import SlackApiError
import sounddevice as sd
import numpy as np
from pydub import AudioSegment
from google.cloud import speech_v1p1beta1 as speech
from pydub.utils import make_chunks
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
import io
import os
import openai
from slack import RTMClient

openai.api_key = 'your-openai-api-key'

call_ongoing = False

@RTMClient.run_on(event="call_started")
def monitor_huddle_start(**payload):
    data = payload['data']
    if 'call_started' in data and data['call_type'] == 'meeting':
        print('Meeting started!')
        start_recording(44100, "recording.wav")

@RTMClient.run_on(event="call_ended")
def monitor_huddle_end(**payload):
    global call_ongoing
    data = payload['data']

    if 'call_ended' in data and data['call_type'] == 'meeting':
        call_ongoing = False
        stop_recording(44100, "recording.wav")
        audio_segments = stop_and_split_recording("recording.wav", 60000)
        for segment in audio_segments:
            transcription = transcribe_segment(segment)
            processed_transcription = process_transcription(transcription)
            post_to_slack_channel(processed_transcription)

rtm_client.start()

def huddle_is_ongoing():
    global call_ongoing
    return call_ongoing

def start_recording(fs, filename):
    global recording
    try:
        recording = sd.rec(int(fs * 2), samplerate=fs, channels=2)
    except Exception as e:
        print(f"Error occurred while starting recording: {e}")

def process_audio(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError("File not found")

def stop_recording(fs, filename):
    global recording
    sd.wait()
    sd.write(filename, recording, fs)
    recording = None

def stop_and_split_recording(filename, chunk_length_ms):
    try:
        audio = AudioSegment.from_file(filename)
        chunks = make_chunks(audio, chunk_length_ms)
        chunk_files = []

        for i, chunk in enumerate(chunks):
            chunk_name = "chunk{0}.wav".format(i)
            chunk.export(chunk_name, format="wav")
            chunk_files.append(chunk_name)

        return chunk_files
    except Exception as e:
        print(f"Error occurred while stopping and splitting recording: {e}")
        

def make_chunks(audio_segment, chunk_length_ms):

   chunks = []

   while len(audio_segment) > chunk_length_ms:
       chunks.append(audio_segment[:chunk_length_ms])  
       audio_segment = audio_segment[chunk_length_ms:]

   return chunks


def transcribe_segment(filename):
    try:
        client = speech.SpeechClient()

        with io.open(filename, "rb") as audio_file:
            content = audio_file.read()

        audio = types.RecognitionAudio(content=content)
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )

        response = client.recognize(config, audio)

        for result in response.results:
            return result.alternatives[0].transcript
    except Exception as e:
        print(f"Error occurred while transcribing segment: {e}")

def process_transcription(transcription):
    try:
        summary_prompt = f"I have a transcription of a meeting and I need a brief 2-line summary. Here is the transcription:\n\n{transcription}\n\nSummarize:"
        summary_response = openai.Completion.create(engine="text-davinci-002", prompt=summary_prompt, max_tokens=60)
        summary = summary_response.choices[0].text.strip()

        tasks_prompt = f"I have a transcription of a meeting and I need to extract any tasks that were discussed. Here is the transcription:\n\n{transcription}\n\nTasks:"
        tasks_response = openai.Completion.create(engine="text-davinci-002", prompt=tasks_prompt, max_tokens=200)
        tasks = tasks_response.choices[0].text.strip()

        notes_prompt = f"I have a transcription of a meeting and I need to extract important notes. Here is the transcription:\n\n{transcription}\n\nNotes:"
        notes_response = openai.Completion.create(engine="text-davinci-002", prompt=notes_prompt, max_tokens=200)
        notes = notes_response.choices[0].text.strip()

        return summary, tasks, notes
    except Exception as e:
        print(f"Error occurred while processing transcription: {e}")

def post_to_slack_channel(message):
    try:
        client = WebClient(token=os.environ['SLACK_API_TOKEN'])
        response = client.chat_postMessage(
            channel='#meeting_recordings',
            text=message)
    except SlackApiError as e:
        print(f"Got an error: {e.response['error']}")

def main():
    while True:
        if monitor_huddle_start():
            start_recording(44100, "recording.wav")
            while huddle_is_ongoing():
                continue
            stop_recording(44100, "recording.wav")
            audio_segments = stop_and_split_recording("recording.wav", 60000)
            for segment in audio_segments:
                transcription = transcribe_segment(segment)
                processed_transcription = process_transcription(transcription)
                post_to_slack_channel(processed_transcription)
                time.sleep(60)

rtm_client = RTMClient(token='your-slack-token')
rtm_client.start()