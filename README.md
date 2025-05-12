# Painel Chamador de Motoristas

## Visão Geral
Este projeto utiliza **Python** e **Streamlit** para criar um painel interativo que permite:
- Cadastrar motoristas e seus destinos em um arquivo CSV.
- Chamar motoristas com o clique de um botão.
- Exibir o status atualizado em tempo real.

## Estrutura do Projeto
```
painel_chamador/
├── chamados.csv
├── painel.py
└── README.md
```

## Como Usar

1. **Instalar dependências**  
   ```bash
   pip install streamlit pandas
   ```

2. **Rodar o painel**  
   ```bash
   streamlit run painel.py
   ```

3. **Acessar no navegador**  
   O painel abrirá em `http://localhost:8501`.

## Observações
- O arquivo `chamados.csv` é atualizado automaticamente pelo Streamlit.
- Para reiniciar o status, edite manualmente o CSV ou extenda o código.
