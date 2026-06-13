import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Languages, Pencil, Plus, X } from 'lucide-react';
import { FormEvent, useState } from 'react';

import {
  createLanguage,
  getLanguages,
  updateLanguage,
} from '../../api/client';
import { Language } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';

type LanguageForm = {
  code: string;
  display_name: string;
  is_active: boolean;
};

const emptyForm: LanguageForm = {
  code: '',
  display_name: '',
  is_active: true,
};

const Settings = () => {
  const queryClient = useQueryClient();
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LanguageForm>(emptyForm);

  const { data: languages = [], isLoading } = useQuery({
    queryKey: ['languages'],
    queryFn: async () => {
      const { data } = await getLanguages();
      return Array.isArray(data) ? data : [];
    },
  });

  const closeForm = () => {
    setShowForm(false);
    setEditingCode(null);
    setForm(emptyForm);
  };

  const saveMutation = useMutation({
    mutationFn: (data: LanguageForm) => {
      if (editingCode) {
        return updateLanguage(editingCode, {
          display_name: data.display_name,
          is_active: data.is_active,
        });
      }
      return createLanguage(data as Omit<Language, 'created_at'>);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] });
      closeForm();
    },
    onError: (error: any) => {
      alert(
        'Failed to save language: ' +
          (error.response?.data?.detail || error.message),
      );
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (language: Language) =>
      updateLanguage(language.code, {
        display_name: language.display_name,
        is_active: !language.is_active,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] });
    },
    onError: (error: any) => {
      alert(
        'Failed to update language: ' +
          (error.response?.data?.detail || error.message),
      );
    },
  });

  const startEdit = (language: Language) => {
    setEditingCode(language.code);
    setForm({
      code: language.code,
      display_name: language.display_name,
      is_active: language.is_active,
    });
    setShowForm(true);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    saveMutation.mutate(form);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xl font-bold text-content-primary">Languages</h3>
          <p className="text-sm text-content-secondary">
            Configure the languages available when creating pipelines.
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingCode(null);
            setForm(emptyForm);
            setShowForm(true);
          }}
          className="flex w-fit items-center gap-2"
        >
          <Plus size={18} />
          Add Language
        </Button>
      </div>

      <Card>
        <CardHeader className="border-b border-border-subtle">
          <CardTitle className="flex items-center gap-2 text-base">
            <Languages size={18} />
            Pipeline Languages
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-content-secondary">Loading languages...</div>
          ) : (
            <div className="divide-y divide-border-subtle">
              {languages.map((language) => (
                <div
                  key={language.code}
                  className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-content-primary">
                        {language.display_name}
                      </span>
                      <code className="rounded bg-surface-subtle px-2 py-0.5 text-xs text-content-secondary">
                        {language.code}
                      </code>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={language.is_active}
                      disabled={toggleMutation.isPending}
                      onClick={() => toggleMutation.mutate(language)}
                      className={`relative h-6 w-11 rounded-full transition-colors disabled:opacity-50 ${
                        language.is_active ? 'bg-accent' : 'bg-border-strong'
                      }`}
                      title={language.is_active ? 'Disable language' : 'Enable language'}
                    >
                      <span
                        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                          language.is_active ? 'translate-x-5' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                    <span className="w-16 text-sm text-content-secondary">
                      {language.is_active ? 'Enabled' : 'Disabled'}
                    </span>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => startEdit(language)}
                      title="Edit language"
                    >
                      <Pencil size={16} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-lg shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border-subtle">
              <CardTitle className="text-lg">
                {editingCode ? 'Edit Language' : 'Add Language'}
              </CardTitle>
              <Button variant="ghost" size="icon" onClick={closeForm}>
                <X size={20} />
              </Button>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4 p-6">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    Language Code
                  </label>
                  <Input
                    required
                    maxLength={12}
                    value={form.code}
                    disabled={!!editingCode}
                    onChange={(event) =>
                      setForm({ ...form, code: event.target.value.toLowerCase() })
                    }
                    placeholder="e.g. de"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    Language Name
                  </label>
                  <Input
                    required
                    value={form.display_name}
                    onChange={(event) =>
                      setForm({ ...form, display_name: event.target.value })
                    }
                    placeholder="e.g. German"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-content-primary">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(event) =>
                      setForm({ ...form, is_active: event.target.checked })
                    }
                  />
                  Available for new pipelines
                </label>
              </CardContent>
              <div className="flex justify-end gap-3 border-t border-border-subtle p-6">
                <Button type="button" variant="ghost" onClick={closeForm}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saveMutation.isPending}>
                  {editingCode ? 'Update Language' : 'Create Language'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Settings;
