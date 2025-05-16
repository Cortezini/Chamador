from pathlib import Path
import os
import hashlib

# Geração segura da SECRET_KEY
if not os.path.exists('.secret_key'):
    with open('.secret_key', 'w') as f:
        f.write(os.urandom(32).hex())

# Leitura correta da chave
with open('.secret_key', 'r') as f:
    SECRET_KEY = f.read().strip().encode()  # String → bytes

CONFIGURACOES = {
    'interface': {
        'titulo_pagina': 'Painel BDM',
        'icone_pagina': 'assets/bdm.ico',
        'layout': 'wide',
        'opcoes_patio': {
            'destinos': ['UNIDADE 1', 'UNIDADE 2', 'NIGRAM'],
            'docas': [f'DOCA {n}' for n in range(1, 9)]
        }
    },
    'validacoes': {
        'telefone': r'^\(\d{2}\) \d{4,5}-\d{4}$',
        'placa': r'^[A-Za-z]{3}[- ]?[\dA-Za-z]{4}$',
        'senha': r'^\d{3}$',
        'nome': r'^[A-Za-zÀ-ÿ\s]{5,}$'
    },
    'audio': {
        'caminho_audio': Path('assets/alerta_sonoro.wav'),
        'taxa_amostragem': 44100,
        'duracao_alerta': 2,
        'frequencia_alerta': 440
    }
}

# Verificação de assets essenciais
if not Path(CONFIGURACOES['interface']['icone_pagina']).exists():
    raise FileNotFoundError("Ícone não encontrado: assets/bdm.ico")

if not CONFIGURACOES['audio']['caminho_audio'].exists():
    # Código para gerar áudio automaticamente
    pass

USUARIOS = {
    b'admin': (
        (
            bytes.fromhex('aa234114199b7a0046bdc2b4c7711b3f870a6f9f49e229b0acd49c8e42e39c00'), 
            bytes.fromhex('1cbb3219f21610021b9ab5b27a20c6bffe4d8b2f5573dda7eb48681b0c761919')
        ),
        'administrador'
    )
}

PERMISSOES = {
    'administrador': [
        'Administrativo',
        'Controle Pátio', 
        'Relatórios', 
        'Informações Motoristas'
    ],
    'patio': [
        'Controle Pátio', 
        'Informações Motoristas'
    ]
}