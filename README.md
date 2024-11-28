# Testes de Latência e Tokenizers em Comunicação de Áudio com WebSockets

Este repositório contém experimentos relacionados à análise de latência em pipelines de comunicação de áudio via WebSockets, utilizando tokenizers e simulações de tráfego controladas com a ferramenta `tc` (Traffic Control). 

## Objetivo

Avaliar o impacto de diferentes tokenizers no desempenho e na latência de transmissão em fluxos de áudio, considerando condições de rede variáveis como baixa largura de banda, alta latência e perda de pacotes. Este estudo é fundamental para melhorar a eficiência de sistemas em tempo real que dependem de redes instáveis.

## Funcionalidades

- Testes de diferentes tokenizers no pipeline de áudio.
- Simulação de condições adversas de rede utilizando o `tc`.
- Coleta e análise de métricas de latência, perda de pacotes e reconstrução do áudio.

## Estrutura do Repositório

```
├── encode/            # Pacotes referentes ao WavTokenizer
├── decode/            # Pacotes referentes ao WavTokenizer
├── *.py               # Scripts de server e client para avaliação das métricas.
├── examples/          # Exemplos da utilização do repositório
├── requiriments.txt   # Pacotes para reprodução dos testes
└── README.md          # Documentação do projeto
```

## Pré-requisitos

Certifique-se de que os seguintes softwares estão instalados no sistema:

- Docker
- Ferramenta `tc` do pacote `iproute2`
- Dependências Python listadas em `requirements.txt` (caso aplicável)

## Configuração do Ambiente

1. Clone este repositório:
   ```bash
   git clone https://github.com/alexandreacff/Audio_Codecs_Streaming.git
   cd Audio_Codecs_Streaming
   ```

2.Configure o ambiente:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure o `tc` para simulação de tráfego. Exemplos estão disponíveis no diretório `examples/`.

4. Download model e o config.yaml em: https://huggingface.co/novateur/WavTokenizer/tree/main
## Como Executar

1. Configure as condições de rede desejadas com o `tc`:
   ```bash
   sudo tc qdisc add dev wlp0s20f3 root tbf rate 1Mbit latency 1000ms burst 1540
   ```

2. Em uma maquina execute o pipeline de fluxo para pegar do microfone:
   ```bash
   python transferencia_fluxo_normal.py # Normal
   python transferencia_fluxo_wavtokenizer.py # Codec
   ```

4. Para remover as configurações do `tc`:
   ```bash
   sudo tc qdisc del dev wlp0s20f3 root
   ```

## Resultados

Os resultados incluem:
- Latência média por teste.
- Impacto da perda de pacotes e latência na reconstrução do áudio.
- Comparação de eficiência entre diferentes tokenizers.
