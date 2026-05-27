import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { getAccounts, deleteAccount, createAccount, updateAccount } from '../../api/client';
import AccountCard from './components/AccountCard';
import AccountForm from './components/AccountForm';
import AccountsSkeleton from './components/AccountsSkeleton';
import { Account } from '../../api/types';
import { Button } from '../../components/ui/Button';

const Accounts = () => {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [activeType, setActiveType] = useState('all');

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const { data } = await getAccounts();
      return data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
    onError: () => {
      alert('Failed to delete account');
    },
  });

  const saveMutation = useMutation({
    mutationFn: (formData: Partial<Account>) => {
      if (editingAccount) {
        return updateAccount(editingAccount.id, formData);
      } else {
        return createAccount(formData);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      setShowForm(false);
      setEditingAccount(null);
    },
    onError: (error: any) => {
      alert('Failed to save account: ' + (error.response?.data?.detail || error.message));
    },
  });

  const types = [
    { id: 'all', label: 'All' },
    { id: 'wp', label: 'WordPress' },
    { id: 'ai', label: 'AI (9router)' },
    { id: 'fb', label: 'Facebook' },
    { id: 'gs', label: 'Google Sheets' },
    { id: 'tg', label: 'Telegram' },
  ];

  const filteredAccounts = activeType === 'all'
    ? accounts
    : accounts.filter(a => a.type === activeType);

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this account?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-content-primary">Service Accounts</h3>
          <p className="text-sm text-content-secondary">Manage your credentials for various services.</p>
        </div>
        <Button
          onClick={() => { setEditingAccount(null); setShowForm(true); }}
          className="flex items-center space-x-2 w-fit"
        >
          <Plus size={18} />
          <span>Add Account</span>
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-1 border-b border-border-default overflow-x-auto no-scrollbar scroll-smooth shrink-0">
        {types.map(type => (
          <button
            key={type.id}
            onClick={() => setActiveType(type.id)}
            className={`px-4 py-2 text-sm font-bold transition-all border-b-2 -mb-px whitespace-nowrap ${
              activeType === type.id
                ? 'border-accent text-accent'
                : 'border-transparent text-content-tertiary hover:text-content-secondary hover:border-border-strong'
            }`}
          >
            {type.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <AccountsSkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          {filteredAccounts.length === 0 ? (
            <div className="col-span-full py-20 text-center bg-surface rounded-xl border border-dashed border-border-strong">
              <p className="text-content-secondary">No {activeType !== 'all' ? activeType.toUpperCase() : ''} accounts configured yet.</p>
            </div>
          ) : (
            filteredAccounts.map((acc) => (
              <AccountCard 
                key={acc.id} 
                account={acc} 
                onEdit={(a) => { setEditingAccount(a); setShowForm(true); }}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      )}

      {showForm && (
        <AccountForm
          account={editingAccount}
          onClose={() => { setShowForm(false); setEditingAccount(null); }}
          onSave={(data) => saveMutation.mutate(data)}
        />
      )}
    </div>
  );
};

export default Accounts;
