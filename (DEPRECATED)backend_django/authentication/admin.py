from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserSession

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface para o modelo User customizado"""
    
    # Campos exibidos na listagem
    list_display = ('username', 'email', 'preferred_name', 'is_admin', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_admin', 'is_staff', 'is_active', 'department', 'created_at')
    search_fields = ('username', 'email', 'preferred_name', 'first_name', 'last_name')
    
    # Ordenação padrão
    ordering = ('-created_at',)
    
    # Campos editáveis na visualização de detalhes
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Microsoft', {
            'fields': ('microsoft_id', 'preferred_name', 'profile_picture')
        }),
        ('Informações Corporativas', {
            'fields': ('department', 'job_title', 'is_admin')
        }),
        ('Preferências', {
            'fields': ('theme_preference',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Campos somente leitura
    readonly_fields = ('created_at', 'updated_at', 'microsoft_id')
    
    # Campos para criar novo usuário
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('email', 'preferred_name', 'department', 'job_title', 'is_admin')
        }),
    )

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface para sessões de usuário"""
    
    list_display = ('user', 'session_token_short', 'expires_at', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'session_token')
    ordering = ('-created_at',)
    
    readonly_fields = ('session_token', 'microsoft_token', 'refresh_token', 'created_at')
    
    def session_token_short(self, obj):
        """Exibe apenas os primeiros 10 caracteres do token"""
        return f"{obj.session_token[:10]}..."
    session_token_short.short_description = 'Token (resumido)'
    
    def has_add_permission(self, request):
        """Desabilita criação manual de sessões"""
        return False