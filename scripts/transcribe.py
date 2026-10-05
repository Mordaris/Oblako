"""Транскрипция референса с пословными таймкодами.

huggingface.co закрыт сетевой политикой облака, поэтому используется GigaAM v2 (русская
RNN-T модель) через sherpa-onnx; модели скачиваются из GitHub-релизов k2-fsa/sherpa-onnx.
Речь режется Silero VAD на фразы, каждая фраза распознаётся отдельно, таймкоды токенов
переводятся в абсолютное время и склеиваются в слова.

Выход: analysis/transcript.json (фразы + слова), analysis/transcript.srt, analysis/transcript.txt
Запуск: python3 scripts/transcribe.py
"""
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
import sherpa_onnx

from refcfg import OUT, SRC

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(os.environ.get("MODELS_DIR", Path.home() / ".cache" / "oblako-models"))   # вне репо; Linux/Mac
REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
GIGA = "sherpa-onnx-nemo-transducer-giga-am-v2-russian-2025-04-19"
SR = 16000


def ensure_models():
    MODELS.mkdir(parents=True, exist_ok=True)
    if not (MODELS / GIGA).exists():
        tar = MODELS / f"{GIGA}.tar.bz2"
        urllib.request.urlretrieve(f"{REL}/{GIGA}.tar.bz2", tar)
        subprocess.run(["tar", "xjf", str(tar), "-C", str(MODELS)], check=True)
        tar.unlink()
    if not (MODELS / "silero_vad.onnx").exists():
        urllib.request.urlretrieve(f"{REL}/silero_vad.onnx", MODELS / "silero_vad.onnx")


def load_audio():
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(SRC), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def srt_ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ensure_models()
    d = MODELS / GIGA
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.onnx"),
        joiner=str(d / "joiner.onnx"), tokens=str(d / "tokens.txt"),
        model_type="nemo_transducer", num_threads=4, sample_rate=SR,
    )
    vcfg = sherpa_onnx.VadModelConfig()
    vcfg.silero_vad.model = str(MODELS / "silero_vad.onnx")
    vcfg.silero_vad.min_silence_duration = 0.15
    vcfg.silero_vad.min_speech_duration = 0.1
    vcfg.silero_vad.max_speech_duration = 15
    vcfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(vcfg, buffer_size_in_seconds=200)

    audio = load_audio()
    win = vcfg.silero_vad.window_size
    chunks = []
    for i in range(0, len(audio), win):
        vad.accept_waveform(audio[i:i + win])
        while not vad.empty():
            chunks.append((vad.front.start, np.array(vad.front.samples)))
            vad.pop()
    vad.flush()
    while not vad.empty():
        chunks.append((vad.front.start, np.array(vad.front.samples)))
        vad.pop()

    phrases, srt, txt = [], [], []
    for n, (start_sample, samples) in enumerate(chunks, 1):
        t0 = start_sample / SR
        s = rec.create_stream()
        s.accept_waveform(SR, samples)
        rec.decode_stream(s)
        r = s.result
        words, cur = [], None
        for tok, t in zip(r.tokens, r.timestamps):  # токены GigaAM — буквы, граница слова — токен " "
            if not tok.strip():
                if cur:
                    words.append(cur)
                cur = None
            elif cur is None:
                cur = {"w": tok, "start": round(t0 + t, 3)}
            else:
                cur["w"] += tok
        if cur:
            words.append(cur)
        for i, w in enumerate(words):  # конец слова = начало следующего, последнее — конец фразы
            w["end"] = words[i + 1]["start"] if i + 1 < len(words) else round(t0 + len(samples) / SR, 3)
        text = r.text.strip()
        if not text:
            continue
        t1 = round(t0 + len(samples) / SR, 3)
        phrases.append({"id": len(phrases) + 1, "start": round(t0, 3), "end": t1, "text": text, "words": words})
        srt.append(f"{len(phrases)}\n{srt_ts(t0)} --> {srt_ts(t1)}\n{text}\n")
        txt.append(f"[{t0:7.2f}-{t1:7.2f}] {text}")
        print(txt[-1], flush=True)

    OUT.mkdir(exist_ok=True)
    meta = {"engine": "sherpa-onnx GigaAM v2 RNN-T + Silero VAD", "duration": len(audio) / SR, "phrases": phrases}
    (OUT / "transcript.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "transcript.srt").write_text("\n".join(srt), encoding="utf-8")
    (OUT / "transcript.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
