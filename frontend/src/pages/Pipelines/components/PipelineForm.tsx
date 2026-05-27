import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getAccounts } from '../../../api/client';
import { Pipeline } from '../../../api/types';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';

interface PipelineFormProps {
  pipeline: Pipeline | null;
  onClose: () => void;
  onSave: (formData: Partial<Pipeline>) => void;
}

const PipelineForm: React.FC<PipelineFormProps> = ({ pipeline, onClose, onSave }) => {
  const [formData, setFormData] = useState<Partial<Pipeline>>({
    name: '',
    language: 'uk',
    step_accounts: {
      ai: '',
      wp: '',
      fb: '',
      gs: '',
      tg: ''
    }
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const { data } = await getAccounts();
      return data;
    },
  });

  useEffect(() => {
    if (pipeline) {
      setFormData(pipeline);
    }
  }, [pipeline]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleStepAccountChange = (step: string, accId: string) => {
    setFormData({
      ...formData,
      step_accounts: {
        ...(formData.step_accounts || {}),
        [step]: accId
      }
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl overflow-hidden shadow-xl border-none">
        <CardHeader className="flex flex-row justify-between items-center border-b border-border-subtle p-6">
          <CardTitle className="text-xl">
            {pipeline ? 'Edit Pipeline' : 'Create New Pipeline'}
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-content-tertiary">
            <X size={24} />
          </Button>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-content-primary">Pipeline Name</label>
                <Input 
                  type="text" 
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Daily News Pipeline"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-content-primary">Language</label>
                <Select 
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                >
                  <option value="uk">Ukrainian</option>
                  <option value="vi">Vietnamese</option>
                  <option value="en">English</option>
                  <option value="hr">Croatian</option>
                  <option value="ro">Romanian</option>
                  <option value="it">Italian</option>
                  <option value="pl">Polish</option>
                </Select>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-bold text-sm text-content-tertiary uppercase tracking-wider">Step Configuration</h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">AI Account (Text/Image)</label>
                  <Select 
                    value={formData.step_accounts?.ai || ''}
                    onChange={(e) => handleStepAccountChange('ai', e.target.value)}
                  >
                    <option value="">-- Select AI --</option>
                    {accounts.filter(a => a.type === 'ai').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">WordPress Account</label>
                  <Select 
                    value={formData.step_accounts?.wp || ''}
                    onChange={(e) => handleStepAccountChange('wp', e.target.value)}
                  >
                    <option value="">-- Select WP --</option>
                    {accounts.filter(a => a.type === 'wp').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">Facebook Page</label>
                  <Select 
                    value={formData.step_accounts?.fb || ''}
                    onChange={(e) => handleStepAccountChange('fb', e.target.value)}
                  >
                    <option value="">-- Select FB --</option>
                    {accounts.filter(a => a.type === 'fb').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">Google Sheets (Log)</label>
                  <Select 
                    value={formData.step_accounts?.gs || ''}
                    onChange={(e) => handleStepAccountChange('gs', e.target.value)}
                  >
                    <option value="">-- Select Sheets --</option>
                    {accounts.filter(a => a.type === 'gs').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">Telegram (Notify)</label>
                  <Select 
                    value={formData.step_accounts?.tg || ''}
                    onChange={(e) => handleStepAccountChange('tg', e.target.value)}
                  >
                    <option value="">-- Select TG --</option>
                    {accounts.filter(a => a.type === 'tg').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </Select>
                </div>
              </div>
            </div>
          </CardContent>

          <CardFooter className="p-6 border-t border-border-subtle flex justify-end space-x-3">
            <Button variant="ghost" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">
              {pipeline ? 'Update Pipeline' : 'Create Pipeline'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

export default PipelineForm;
