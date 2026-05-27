import React, { useState } from 'react';
import { RefreshCw, Edit2, Trash2, CheckCircle, XCircle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { testAccount } from '../../../api/client';
import { Account } from '../../../api/types';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';

interface AccountCardProps {
  account: Account;
  onEdit: (account: Account) => void;
  onDelete: (id: string) => void;
}

const AccountCard: React.FC<AccountCardProps> = ({ account, onEdit, onDelete }) => {
  const [testResult, setTestResult] = useState<{ success: boolean; message?: string } | null>(null);

  const testMutation = useMutation({
    mutationFn: () => testAccount({ id: account.id }),
    onSuccess: () => setTestResult({ success: true }),
    onError: (error: any) => setTestResult({ 
      success: false, 
      message: error.response?.data?.detail || 'Test failed' 
    }),
  });

  return (
    <Card className="hover:shadow-md transition-shadow group">
      <CardHeader className="p-6 pb-4">
        <div className="flex justify-between items-start">
          <div className="overflow-hidden">
            <CardTitle className="group-hover:text-accent transition-colors">{account.name}</CardTitle>
            <span className="text-[10px] uppercase font-bold tracking-widest text-content-tertiary bg-canvas px-2 py-0.5 rounded border border-border-subtle">
              {account.type}
            </span>
          </div>
          <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
              title="Test Connection"
              className="h-8 w-8 text-content-tertiary hover:text-accent"
            >
              <RefreshCw size={16} className={testMutation.isPending ? 'animate-spin' : ''} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onEdit(account)}
              title="Edit Account"
              className="h-8 w-8 text-content-tertiary hover:text-status-warning"
            >
              <Edit2 size={16} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(account.id)}
              title="Delete Account"
              className="h-8 w-8 text-content-tertiary hover:text-status-danger"
            >
              <Trash2 size={16} />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-0">
        <div className="text-xs text-content-secondary space-y-1 mb-4 font-mono overflow-hidden">
          {account.type === 'wp' && <p className="truncate">URL: {account.config.url}</p>}
          {account.type === 'ai' && <p className="truncate">Model: {account.config.text_model}</p>}
          {account.type === 'fb' && <p className="truncate">Page: {account.config.page_id}</p>}
          {account.type === 'gs' && <p className="truncate">Sheet ID: {account.config.spreadsheet_id}</p>}
          {account.type === 'tg' && <p className="truncate">Chat ID: {account.config.chat_id}</p>}
        </div>

        {testResult && (
          <div className={`flex items-center space-x-2 text-[11px] font-semibold p-2 rounded-lg ${
            testResult.success ? 'bg-status-success/10 text-status-success' : 'bg-status-danger/10 text-status-danger'
          }`}>
            {testResult.success ? (
              <><CheckCircle size={14} /> <span>Verified</span></>
            ) : (
              <><XCircle size={14} /> <span className="truncate">{testResult.message}</span></>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AccountCard;
