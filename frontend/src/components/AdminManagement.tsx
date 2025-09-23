import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Alert } from './ui/alert';
import { Loader2, Plus, Trash2, Shield, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

interface AdminListResponse {
  admins: string[];
  count: number;
}

export default function AdminManagement() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [admins, setAdmins] = useState<string[]>([]);
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [processingEmail, setProcessingEmail] = useState<string | null>(null);

  // Fetch admin list
  const fetchAdmins = async () => {
    setLoading(true);
    try {
      const response = await api.get<AdminListResponse>('/admin/list');
      setAdmins(response.data.admins);
    } catch (error) {
      console.error('Error fetching admins:', error);
      setMessage({ type: 'error', text: t('settings.error_loading_admins') });
    } finally {
      setLoading(false);
    }
  };

  // Add new admin
  const handleAddAdmin = async () => {
    if (!newAdminEmail || !newAdminEmail.includes('@')) {
      setMessage({ type: 'error', text: t('settings.error_invalid_email') });
      return;
    }

    setProcessingEmail(newAdminEmail);
    try {
      const response = await api.post('/admin/add', { email: newAdminEmail });

      if (response.data.success) {
        setMessage({ type: 'success', text: response.data.message });
        setNewAdminEmail('');
        await fetchAdmins(); // Refresh list
      } else {
        setMessage({ type: 'error', text: response.data.message });
      }
    } catch (error: any) {
      console.error('Error adding admin:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || t('settings.error_adding_admin')
      });
    } finally {
      setProcessingEmail(null);
    }
  };

  // Remove admin
  const handleRemoveAdmin = async (email: string) => {
    // Confirm before removing
    if (!window.confirm(t('settings.remove_admin_confirm', { email }))) {
      return;
    }

    setProcessingEmail(email);
    try {
      const response = await api.delete(`/api/admin/remove/${email}`);

      if (response.data.success) {
        setMessage({ type: 'success', text: response.data.message });
        await fetchAdmins(); // Refresh list
      } else {
        setMessage({ type: 'error', text: response.data.message });
      }
    } catch (error: any) {
      console.error('Error removing admin:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || t('settings.error_removing_admin')
      });
    } finally {
      setProcessingEmail(null);
    }
  };

  // Load admins on mount
  useEffect(() => {
    if (user?.is_admin) {
      fetchAdmins();
    }
  }, [user]);

  // Clear message after 5 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  // Only show for admins
  if (!user?.is_admin) {
    return null;
  }

  return (
    <Card className="p-6 bg-gradient-to-br from-card to-card/45 border border-border">
      <div className="flex items-center mb-6">
        <Shield className="h-6 w-6 mr-3 text-knight-gold" />
        <h3 className="text-xl font-semibold text-white">{t('settings.admin_management')}</h3>
      </div>

      {/* Message Alert */}
      {message && (
        <Alert className={`mb-4 ${message.type === 'success' ? 'border-green-500' : 'border-red-500'}`}>
          <div className="flex items-center">
            {message.type === 'success' ? (
              <CheckCircle className="h-5 w-5 mr-2 text-green-500" />
            ) : (
              <AlertCircle className="h-5 w-5 mr-2 text-red-500" />
            )}
            <span className={message.type === 'success' ? 'text-green-200' : 'text-red-200'}>
              {message.text}
            </span>
          </div>
        </Alert>
      )}

      {/* Add New Admin Section */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {t('settings.add_new_admin')}
        </label>
        <div className="flex gap-2">
          <Input
            type="email"
            value={newAdminEmail}
            onChange={(e) => setNewAdminEmail(e.target.value)}
            placeholder="email@semcon.com"
            className="flex-1 bg-background/50 border-knight-steel text-white"
            disabled={processingEmail !== null}
          />
          <Button
            onClick={handleAddAdmin}
            disabled={processingEmail !== null || !newAdminEmail}
            className="bg-knight-gold hover:bg-knight-gold/90 text-knight-dark"
          >
            {processingEmail === newAdminEmail ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Plus className="h-4 w-4 mr-1" />
                {t('settings.add_button')}
              </>
            )}
          </Button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          {t('settings.admin_privilege_info')}
        </p>
      </div>

      {/* Current Admins List */}
      <div>
        <h4 className="text-sm font-medium text-gray-300 mb-3">
          {t('settings.current_admins')} ({admins.length})
        </h4>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-knight-gold" />
          </div>
        ) : (
          <div className="space-y-2">
            {admins.map((email) => (
              <div
                key={email}
                className="flex items-center justify-between p-3 bg-background/30 rounded-lg border border-knight-steel/30"
              >
                <div className="flex items-center">
                  <Shield className="h-4 w-4 mr-3 text-knight-gold/70" />
                  <span className="text-white">
                    {email}
                    {email === user?.email && (
                      <span className="ml-2 text-xs text-gray-400">{t('settings.you_label')}</span>
                    )}
                  </span>
                </div>

                {email !== user?.email && admins.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveAdmin(email)}
                    disabled={processingEmail === email}
                    className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                  >
                    {processingEmail === email ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {admins.length === 0 && !loading && (
          <div className="text-center py-8 text-gray-400">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Nenhum administrador configurado</p>
          </div>
        )}

        {/* Warning about minimum admin requirement */}
        {admins.length === 1 && (
          <Alert className="mt-4 border-yellow-600">
            <AlertCircle className="h-4 w-4 text-yellow-500" />
            <span className="text-yellow-200 ml-2">
              O sistema precisa ter pelo menos um administrador
            </span>
          </Alert>
        )}
      </div>
    </Card>
  );
}