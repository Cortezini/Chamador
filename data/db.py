from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime
from sqlalchemy.exc import NoSuchTableError

SQLITE_FILE = 'registros_chamados.db'
ENGINE = create_engine(f'sqlite:///{SQLITE_FILE}', connect_args={"check_same_thread": False})
META = MetaData()

def criar_tabela_if_not_exists():
    try:
        Table('chamados', META, autoload_with=ENGINE)
    except NoSuchTableError:
        Table('chamados', META,
            Column('motorista', String),
            Column('contato', String),
            Column('transportadora', String),
            Column('senha', String),
            Column('placa', String),
            Column('cliente', String),
            Column('vendedor', String),
            Column('destino', String),
            Column('doca', String),
            Column('status', String),
            Column('chamado_em', DateTime),
            Column('finalizado_em', DateTime)
        )
        META.create_all(ENGINE)