import asyncio
import websockets
import pyaudio
import numpy as np
import json
import base64
import audioop
import time

from encoder.utils import convert_audio
import torchaudio
import torch
from decoder.pretrained import WavTokenizer
import numpy as np

def cut_or_pad_audio(audio, target_length, padding_value=0):
    """
    Ajusta o comprimento de um tensor de áudio de forma [1, N],
    cortando ou preenchendo nas extremidades.

    Parâmetros:
    - audio (torch.Tensor): Sinal de áudio no formato [1, N].
    - target_length (int): Comprimento desejado (N-alvo).
    - padding_value (int ou float): Valor usado para preenchimento, padrão é 0.

    Retorno:
    - torch.Tensor: Sinal ajustado ao comprimento desejado [1, target_length].
    """

    if isinstance(audio, (np.ndarray, list, tuple)):
        audio = torch.from_numpy(audio).unsqueeze(dim=0)

    # Confirme que o áudio tem a forma esperada
    if audio.dim() != 2 or audio.size(0) != 1:
        raise ValueError("O tensor de áudio deve ter a forma [1, N]")

    current_length = audio.size(1)

    if current_length > target_length:
        # Corte centralizado
        start_idx = (current_length - target_length) // 2
        return audio[:, start_idx:start_idx + target_length]

    elif current_length < target_length:
        # Padding centralizado
        pad_left = (target_length - current_length) // 2
        pad_right = target_length - current_length - pad_left
        return torch.nn.functional.pad(audio, (pad_left, pad_right), "constant", padding_value)

    else:
        # Já está no tamanho correto
        return audio


class CodecSpeechLM:
  def __init__(self, model_path, config_path):

    self.device = "cpu"

    self.model = WavTokenizer.from_pretrained0802(config_path, model_path)
    self.model =  self.model.to(self.device)

  def load_audio(self, audio_path, target_length):

    wav, sr = torchaudio.load(audio_path)
    wav = convert_audio(wav, sr, 24000, 1)
    wav = cut_or_pad_audio(wav, target_length*24000, padding_value=0)

    bandwidth_id = torch.tensor([0])
    wav=wav.to(self.device)

    return wav, bandwidth_id

  def discretize(self, wav, bandwidth_id):

    # Convert audio to tokens
    features,discrete_code= self.model.encode_infer(wav, bandwidth_id=bandwidth_id)
    return discrete_code

  def save_tokens(self, tokens, bandwidth_id, output_path):
    tokens = tokens.cpu().numpy()
    bandwidth_id = bandwidth_id.cpu().numpy()
    np.savez(output_path, tokens=tokens, bandwidth_id=bandwidth_id)

  def load_tokens(self, tokens_path):
    tokens_data = np.load(tokens_path)
    return tokens_data['tokens'], tokens_data['bandwidth_id']


class MicReader:
    def __init__(self):
        self.audio = pyaudio.PyAudio()

        self.input_device_index = self.print_devices_input()
        self.rate = int(self.audio.get_device_info_by_index(self.input_device_index)['defaultSampleRate'])
        self.chunk = self.rate // 10
        self.format = pyaudio.paInt16
        self.channels = 1
        self.target_rate = 24000

        print("\n\n\n", 25 * "==", "AUDIO SETTINGS", 25 * "==")
        print(f"input_device_index: {self.input_device_index}")
        print(f"rate: {self.rate}")
        print(f"chunk: {self.chunk}")
        print(f"format: {self.format}")
        print(f"channels: {self.channels}")
        print(f"target_rate: {self.target_rate}")

        # Abrir o stream com exception_on_overflow=False para evitar overflow
        self.stream = self.audio.open(format=self.format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk,
                                      input_device_index=self.input_device_index)
        self.stop_reading = False
        self.cvstate = None

    def read_chunk_stream(self, chunk):
        data = self.stream.read(chunk, exception_on_overflow=False)
        newdata, self.cvstate = audioop.ratecv(data, 2, self.channels, self.rate, self.target_rate, self.cvstate)
        return newdata

    def close_mic(self):
        self.stop_reading = True
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

    def print_devices_input(self):
        print("\n\n\n",25*"==", "INPUT DEVICES", 25*"==")
        print("Available audio input devices:")
        for i in range(self.audio.get_device_count()):
            dev = self.audio.get_device_info_by_index(i)
            if dev.get('maxInputChannels') > 0:
                print(f"Device ID {i}: {dev['name']}")
                print(f"  Default Sample Rate: {dev['defaultSampleRate']}")
        return int(input("Digite o ID do dispositivo de entrada: "))
    
    def resample_audio(self, data, input_rate, output_rate):
        audio_data = np.frombuffer(data, dtype=np.int16)
        duration = len(audio_data) / input_rate
        time_old = np.linspace(0, duration, len(audio_data))
        time_new = np.linspace(0, duration, int(len(audio_data) * output_rate / input_rate))
        resampled_audio = np.interp(time_new, time_old, audio_data).astype(np.int16)
        return resampled_audio.tobytes()

async def send_audio(websocket, stream_id, data, is_first_packet=False):
    audio_chunk_base64 = base64.b64encode(data).decode('utf-8')
    timestamp = time.time()  # Adiciona o timestamp
    message = {
        "id": stream_id,
        "details": audio_chunk_base64,
        "timestamp": timestamp  # Envia o timestamp junto
    }
    await websocket.send(json.dumps(message))

async def main():
    mic = MicReader()
    codec = CodecSpeechLM("./WavTokenizer_small_320_24k_4096.ckpt", "./WavTokenizer/configs/wavtokenizer_smalldata_frame75_3s_nq1_code4096_dim512_kmeans200_attn.yaml")
    latencies = []  # Lista para armazenar as latências

    async with websockets.connect("ws://localhost:8767") as websocket:
        try:
            while not mic.stop_reading:
                data = mic.read_chunk_stream(mic.chunk)
                inicio = time.time()
                _ ,discrete_code= codec.model.encode_infer(torch.tensor(list(data), dtype=torch.int16).unsqueeze(0).float(), bandwidth_id=torch.tensor([0]))
                print(discrete_code.shape)
                data = discrete_code.cpu().numpy().tobytes()
                infer_time = (time.time()-inicio) * 1000
                print("Tempo de processamento: ", (time.time()-inicio) * 1000, "ms")
                await send_audio(websocket, "stream1", data)

                # Aguarda resposta do servidor com o mesmo timestamp
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg_data = json.loads(message)

                    if "timestamp" in msg_data:
                        sent_timestamp = msg_data["timestamp"]
                        latency_rede = (time.time() - sent_timestamp) * 1000  # Calcula latência em ms
                        latency = infer_time + latency_rede
                        latencies.append(latency)

                        # Média da latência a cada 10 pacotes
                        if len(latencies) >= 100:
                            avg_latency = sum(latencies[-100:]) / 100
                            print(f"Média da latência nos últimos 10 pacotes: {avg_latency:.2f} ms")
                        else:
                            print(f"Latência: {latency:.2f} ms")

                except asyncio.TimeoutError:
                    print("Sem resposta do servidor.")

        except KeyboardInterrupt:
            print("Encerrando transmissão.")
        finally:
            mic.close_mic()

if __name__ == "__main__":
    asyncio.run(main())
