import asyncio
import websockets
import pyaudio
import numpy as np
import json
import base64
import audioop
import time

class MicReader:
    def __init__(self):
        self.audio = pyaudio.PyAudio()

        self.input_device_index = self.print_devices_input()
        self.rate = int(self.audio.get_device_info_by_index(self.input_device_index)['defaultSampleRate'])
        self.chunk = self.rate // 1
        self.format = pyaudio.paFloat32
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
    latencies = []  # Lista para armazenar as latências

    async with websockets.connect("ws://localhost:8767") as websocket:
        try:
            while not mic.stop_reading:
                data = mic.read_chunk_stream(mic.chunk)
                await send_audio(websocket, "stream1", data)

                # Aguarda resposta do servidor com o mesmo timestamp
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg_data = json.loads(message)

                    if "timestamp" in msg_data:
                        sent_timestamp = msg_data["timestamp"]
                        latency = (time.time() - sent_timestamp) * 1000  # Calcula latência em ms
                        latencies.append(latency)

                        # Média da latência a cada 10 pacotes
                        if len(latencies) >= 20:
                            avg_latency = sum(latencies[-20:]) / 20
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
