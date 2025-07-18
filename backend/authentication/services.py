import jwt
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
import msal
import base64

class MicrosoftAuthService:
    """Serviço para integração com Microsoft Azure AD"""
    
    @staticmethod
    def get_auth_url(state=None):
        """Gera URL de autenticação Microsoft"""
        app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}",
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )
        
        auth_url = app.get_authorization_request_url(
            scopes=["User.Read", "User.ReadBasic.All", "offline_access"],
            redirect_uri=settings.AZURE_AD_REDIRECT_URI,
            state=state
        )
        
        return auth_url
    
    @staticmethod
    def exchange_code_for_token(code, state=None):
        """Troca código de autorização por token de acesso"""
        app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}",
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )
        
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=["User.Read", "User.ReadBasic.All", "offline_access"],
            redirect_uri=settings.AZURE_AD_REDIRECT_URI
        )
        
        if "error" in result:
            raise ValidationError(f"Erro na autenticação: {result.get('error_description')}")
        
        return result
    
    @staticmethod
    def verify_token(token):
        """Verifica e decodifica token Microsoft"""
        try:
            # Buscar chaves públicas da Microsoft
            keys_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
            keys_response = requests.get(keys_url)
            keys = keys_response.json()
            
            # Decodificar header do token para pegar o kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header['kid']
            
            # Encontrar a chave correta
            key = None
            for k in keys['keys']:
                if k['kid'] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                    break
            
            if not key:
                raise ValidationError("Chave de verificação não encontrada")
            
            # Verificar e decodificar o token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=settings.AZURE_AD_CLIENT_ID,
                issuer=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValidationError("Token expirado")
        except jwt.InvalidTokenError as e:
            raise ValidationError(f"Token inválido: {str(e)}")
    
    @staticmethod
    def get_user_info(access_token):
        """Busca informações do usuário no Microsoft Graph"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValidationError("Erro ao buscar informações do usuário")
        
        return response.json()
    
    @staticmethod
    def refresh_token(refresh_token):
        """Renova token usando refresh token"""
        app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}",
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )
        
        result = app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=["User.Read", "User.ReadBasic.All", "offline_access"]
        )
        
        if "error" in result:
            raise ValidationError(f"Erro ao renovar token: {result.get('error_description')}")
        
        return result
    
    @staticmethod
    def get_user_photo(access_token):
        """Busca foto do perfil do usuário no Microsoft Graph"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Primeiro, verificar se o usuário tem uma foto
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/photo',
                headers=headers
            )
            
            if response.status_code == 404:
                # Usuário não tem foto de perfil
                return None
            
            if response.status_code != 200:
                # Outro erro, mas não deve quebrar o login
                print(f"Erro ao verificar foto do perfil: {response.status_code} - {response.text}")
                return None
            
            # Buscar o conteúdo da foto
            photo_response = requests.get(
                'https://graph.microsoft.com/v1.0/me/photo/$value',
                headers=headers
            )
            
            if photo_response.status_code == 200:
                return photo_response.content
            else:
                print(f"Erro ao baixar foto do perfil: {photo_response.status_code}")
                return None
                
        except Exception as e:
            # Não deve quebrar o login se a foto falhar
            print(f"Erro ao buscar foto do usuário: {str(e)}")
            return None
    
    @staticmethod
    def save_user_photo(user, photo_content):
        """Salva a foto do perfil do usuário"""
        if not photo_content:
            return
        
        try:
            # Criar nome único para o arquivo
            filename = f"profile_{user.microsoft_id}.jpg"
            
            # Salvar a foto no campo ImageField
            user.profile_picture.save(
                filename,
                ContentFile(photo_content),
                save=True
            )
            
            print(f"Foto do perfil salva para o usuário {user.email}")
            
        except Exception as e:
            print(f"Erro ao salvar foto do perfil: {str(e)}")