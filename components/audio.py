# components/audio.py
import pygame
import numpy as np
from pathlib import Path
from data.config import CONFIGURACOES

class AudioManager:
    _initialized = False
    
    @classmethod
    def inicializar(cls):
        if not cls._initialized:
            pygame.mixer.init()
            cls._initialized = True

    @classmethod
    def gerar_audio_alerta(cls):
        """Gera e salva o áudio de alerta usando Pygame"""
        config = CONFIGURACOES['audio']
        taxa_amostragem = config['taxa_amostragem']
        duracao = config['duracao_alerta']
        frequencia = config['frequencia_alerta']

        # Gerar onda senoidal
        t = np.linspace(0, duracao, int(taxa_amostragem * duracao), False)
        onda = 0.5 * np.sin(2 * np.pi * frequencia * t)
        audio = np.int16(onda * 32767)

        # Converter para formato Pygame
        som = pygame.sndarray.make_sound(audio)
        return som

    @classmethod
    def reproduzir_alerta(cls):
        """Reproduz o alerta sonoro usando Pygame"""
        cls.inicializar()
        
        try:
            config = CONFIGURACOES['audio']
            caminho_audio = config['caminho_audio']
            
            if caminho_audio.exists():
                som = pygame.mixer.Sound(str(caminho_audio))
            else:
                som = cls.gerar_audio_alerta()
                pygame.mixer.Sound.save(som, str(caminho_audio))
            
            som.play()
            return True
        except Exception as e:
            print(f"Erro ao reproduzir áudio: {e}")
            return False