from vosk import Model, KaldiRecognizer
import wave
import json
import ffmpeg
import os

# Путь к модели
MODEL_PATH = "./voice_models/vosk-model-ru-0.42"
INPUT_OGG = "audio.ogg"
OUTPUT_WAV = "audio.wav"

# 1. Загрузка модели
if not os.path.isdir(MODEL_PATH):
    raise FileNotFoundError(f"Модель не найдена: {os.path.abspath(MODEL_PATH)}")
model = Model(MODEL_PATH)

# 2. Конвертация OGG → WAV (16 кГц, моно, 16 бит PCM)
ffmpeg.input(INPUT_OGG).output(
    OUTPUT_WAV,
    ar=16000,
    ac=1,
    acodec='pcm_s16le',
    f='wav'
).overwrite_output().run()

# 3. Распознавание
sample_rate = 16000
rec = KaldiRecognizer(model, sample_rate)
rec.SetWords(True)

with wave.open(OUTPUT_WAV, "rb") as wf:
    # Дополнительная проверка (опционально)
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
        raise ValueError("Аудиофайл должен быть моно, 16 бит, PCM")

    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if "text" in result and result["text"]:
                print(result["text"])

    final_result = json.loads(rec.FinalResult())
    if "text" in final_result and final_result["text"]:
        print(final_result["text"])