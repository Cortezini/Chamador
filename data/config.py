from pathlib import Path

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

USUARIOS = {
    "1": ("1", "administrador"),
    "OPERADOR": ("op@2025", "patio")
}

PERMISSOES = {
    'administrador': ['Administrativo', 'Controle Pátio', 'Relatórios', 'Informações Motoristas'],
    'patio': ['Controle Pátio', 'informações Motoristas']
}