# components/audio.py
import os
import pygame
import numpy as np
import streamlit as st
from pathlib import Path
from data.config import CONFIGURACOES

class AudioManager:
    _initialized = False
    
    @classmethod
    def inicializar(cls):
        if not cls._initialized:
            # Configuração para ambientes headless
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
            os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
            
            try:
                pygame.mixer.init()
                cls._initialized = True
            except pygame.error as e:
                st.error(f"Erro de inicialização de áudio: {str(e)}")
                cls._initialized = False

    @classmethod
    def reproduzir_alerta(cls):
        """Reproduz o alerta sonoro com fallback seguro"""
        if not cls.inicializar():
            return False

        try:
            config = CONFIGURACOES['audio']
            caminho_audio = config['caminho_audio']
            
            if caminho_audio.exists():
                som = pygame.mixer.Sound(str(caminho_audio))
            else:
                som = cls.gerar_audio_alerta()
                som.save(str(caminho_audio))
            
            pygame.mixer.Sound.play(som)
            return True
        except Exception as e:
            st.error(f"Erro de áudio: {str(e)}")
            return False

    @classmethod
    def inicializar(cls):
        if not cls._initialized:
            try:
                # Tenta inicializar com configurações seguras
                pygame.mixer.pre_init(44100, -16, 2, 1024)
                pygame.mixer.init()
                cls._initialized = True
            except pygame.error as e:
                print(f"Audio disabled: {str(e)}")
                cls._initialized = False
        return cls._initialized