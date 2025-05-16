import streamlit as st
import hashlib
import time
from itsdangerous import URLSafeSerializer
from data.config import SECRET_KEY

class AuthManager:
    def __init__(self):
        self.serializer = URLSafeSerializer(SECRET_KEY)
        self.cookie_name = "bdm_auth"
        
    def _get_cookie(self):
        """Obtém o cookie via JavaScript"""
        return st.query_params.get(self.cookie_name, [None])[0]
    
    def _set_cookie(self, value, expires_days=30):
        """Define o cookie via JavaScript"""
        js = f"""
        document.cookie = "{self.cookie_name}={value}; 
            path=/; 
            max-age={expires_days*24*60*60}; 
            Secure; 
            SameSite=Lax";
        """
        st.components.v1.html(f"<script>{js}</script>", height=0)
    
    def _generate_token(self, username):
        """Gera token seguro com validade de 30 dias"""
        payload = {
            'user': username,
            'exp': time.time() + 30*24*60*60  # 30 dias
        }
        return self.serializer.dumps(payload)
    
    def validate_token(self):
        """Valida o token do cookie e mantém a sessão"""
        token = self._get_cookie()
        if not token:
            return False
            
        try:
            payload = self.serializer.loads(token)
            if payload['exp'] > time.time():
                st.session_state.update({
                    'logged_in': True,
                    'user': payload['user'],
                    'user_role': self._get_user_role(payload['user'])
                })
                return True
        except:
            return False
    
    def login(self, username, password):
        """Processa o login e seta o cookie"""
        user = self._validate_credentials(username, password)
        if user:
            token = self._generate_token(username)
            self._set_cookie(token)
            return True
        return False
    
    def logout(self):
        """Remove o cookie e limpa a sessão"""
        self._set_cookie('', expires_days=-1)
        st.session_state.clear()
    
    def _validate_credentials(self, username, password):
        """Valida credenciais com bytes corretamente"""
        from data.config import USUARIOS
    
        # Converter para bytes
        username_bytes = username.strip().upper().encode('utf-8')
        stored_data = USUARIOS.get(username_bytes)
    
        if not stored_data:
            return False
        
        # Extrair salt e key
        salt, key = stored_data[0]
    
        # Gerar hash
        new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
        )
    
        return new_hash == key
    
    def _get_user_role(self, username):
        """Obtém o papel do usuário"""
        from data.config import USUARIOS
        return USUARIOS.get(username.upper(), ('', 'visitante'))[1]