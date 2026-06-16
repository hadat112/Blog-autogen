import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ChevronRight,
  Languages,
  Pencil,
  Plus,
  Save,
  Settings as SettingsIcon,
  X,
} from 'lucide-react';
import { FormEvent, useState } from 'react';

import {
  createLanguage,
  getLanguages,
  getSettings,
  updateLanguage,
  updateSettings,
} from '../../api/client';
import { AppSettings, Language } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';

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

const concurrencyPresets = [
  { value: 1, label: 'Safe' },
  { value: 2, label: 'Recommended' },
  { value: 3, label: 'Fast' },
];

type SettingsScreen = 'menu' | 'translation' | 'languages';

const Settings = () => {
  const queryClient = useQueryClient();
  const [activeScreen, setActiveScreen] = useState<SettingsScreen>('menu');
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LanguageForm>(emptyForm);
  const [settingsForm, setSettingsForm] = useState<AppSettings>({
    translation_mode: 'sequential',
    translation_max_concurrency: 2,
    ai_request_timeout: 300,
    translation_chunk_size: 6000,
  });

  const { data: languages = [], isLoading } = useQuery({
    queryKey: ['languages'],
    queryFn: async () => {
      const { data } = await getLanguages();
      return Array.isArray(data) ? data : [];
    },
  });

  const { isLoading: isSettingsLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const { data } = await getSettings();
      const settings = {
        translation_mode: data.translation_mode || 'sequential',
        translation_max_concurrency: data.translation_max_concurrency || 2,
        ai_request_timeout: data.ai_request_timeout || 300,
        translation_chunk_size: data.translation_chunk_size || 6000,
      } as AppSettings;
      setSettingsForm(settings);
      return settings;
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

  const settingsMutation = useMutation({
    mutationFn: (data: AppSettings) => updateSettings(data),
    onSuccess: ({ data }) => {
      setSettingsForm(data);
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (error: any) => {
      alert(
        'Failed to save settings: ' +
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

  const saveSettings = (event: FormEvent) => {
    event.preventDefault();
    settingsMutation.mutate({
      translation_mode: settingsForm.translation_mode,
      translation_max_concurrency: Math.min(
        8,
        Math.max(1, Number(settingsForm.translation_max_concurrency) || 2),
      ),
      ai_request_timeout: Math.min(
        900,
        Math.max(30, Number(settingsForm.ai_request_timeout) || 300),
      ),
      translation_chunk_size: Math.min(
        30000,
        Math.max(1000, Number(settingsForm.translation_chunk_size) || 6000),
      ),
    });
  };

  if (activeScreen === 'menu') {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-xl font-bold text-content-primary">Settings</h3>
          <p className="text-sm text-content-secondary">
            Choose a settings area to configure.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <button
            type="button"
            onClick={() => setActiveScreen('translation')}
            className="flex items-center justify-between rounded-md border border-border-default bg-surface p-4 text-left shadow-sm transition-colors hover:bg-surface-subtle"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-surface-subtle text-content-primary">
                <SettingsIcon size={18} />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-content-primary">
                  Translation Settings
                </div>
                <div className="text-sm text-content-secondary">
                  Chunk mode, concurrency, and context behavior.
                </div>
              </div>
            </div>
            <ChevronRight size={18} className="shrink-0 text-content-secondary" />
          </button>

          <button
            type="button"
            onClick={() => setActiveScreen('languages')}
            className="flex items-center justify-between rounded-md border border-border-default bg-surface p-4 text-left shadow-sm transition-colors hover:bg-surface-subtle"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-surface-subtle text-content-primary">
                <Languages size={18} />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-content-primary">
                  Languages
                </div>
                <div className="text-sm text-content-secondary">
                  Available languages for new pipelines.
                </div>
              </div>
            </div>
            <ChevronRight size={18} className="shrink-0 text-content-secondary" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {activeScreen === 'translation' && (
      <>
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => setActiveScreen('menu')}
          title="Back to settings"
        >
          <ArrowLeft size={18} />
        </Button>
        <div>
          <h3 className="text-xl font-bold text-content-primary">
            Translation Settings
          </h3>
          <p className="text-sm text-content-secondary">
            Configure chunk processing for article translation.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="border-b border-border-subtle">
          <CardTitle className="flex items-center gap-2 text-base">
            <SettingsIcon size={18} />
            Translation Settings
          </CardTitle>
        </CardHeader>
        <form onSubmit={saveSettings}>
          <CardContent className="space-y-5 p-5">
            {isSettingsLoading ? (
              <div className="text-sm text-content-secondary">Loading settings...</div>
            ) : (
              <>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-content-primary">
                      Chunk Mode
                    </label>
                    <Select
                      value={settingsForm.translation_mode}
                      onChange={(event) =>
                        setSettingsForm({
                          ...settingsForm,
                          translation_mode: event.target.value as AppSettings['translation_mode'],
                        })
                      }
                    >
                      <option value="sequential">Sequential</option>
                      <option value="parallel">Parallel</option>
                    </Select>
                    <p className="text-xs leading-5 text-content-secondary">
                      Sequential keeps translated context from the previous chunk.
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-content-primary">
                      Max Concurrency
                    </label>
                    <Input
                      type="number"
                      min={1}
                      max={8}
                      value={settingsForm.translation_max_concurrency}
                      disabled={settingsForm.translation_mode === 'sequential'}
                      onChange={(event) =>
                        setSettingsForm({
                          ...settingsForm,
                          translation_max_concurrency: Number(event.target.value),
                        })
                      }
                    />
                    <p className="text-xs leading-5 text-content-secondary">
                      Parallel uses previous source text as context and preserves chunk order.
                    </p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {concurrencyPresets.map((preset) => (
                        <Button
                          key={preset.value}
                          type="button"
                          variant={
                            settingsForm.translation_max_concurrency === preset.value
                              ? 'secondary'
                              : 'outline'
                          }
                          size="sm"
                          disabled={settingsForm.translation_mode === 'sequential'}
                          onClick={() =>
                            setSettingsForm({
                              ...settingsForm,
                              translation_max_concurrency: preset.value,
                            })
                          }
                          title={`Use concurrency ${preset.value}`}
                        >
                          {preset.value} {preset.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-content-primary">
                      AI Timeout
                    </label>
                    <Input
                      type="number"
                      min={30}
                      max={900}
                      value={settingsForm.ai_request_timeout}
                      onChange={(event) =>
                        setSettingsForm({
                          ...settingsForm,
                          ai_request_timeout: Number(event.target.value),
                        })
                      }
                    />
                    <p className="text-xs leading-5 text-content-secondary">
                      Seconds to wait for each AI text request before retrying.
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-content-primary">
                      Text Per Chunk
                    </label>
                    <Input
                      type="number"
                      min={1000}
                      max={30000}
                      step={500}
                      value={settingsForm.translation_chunk_size}
                      onChange={(event) =>
                        setSettingsForm({
                          ...settingsForm,
                          translation_chunk_size: Number(event.target.value),
                        })
                      }
                    />
                    <p className="text-xs leading-5 text-content-secondary">
                      Maximum characters sent in each translated article chunk.
                    </p>
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    className="flex items-center gap-2"
                    disabled={settingsMutation.isPending}
                  >
                    <Save size={16} />
                    Save Settings
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </form>
      </Card>
      </>
      )}

      {activeScreen === 'languages' && (
      <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={() => setActiveScreen('menu')}
            title="Back to settings"
          >
            <ArrowLeft size={18} />
          </Button>
          <div>
            <h3 className="text-xl font-bold text-content-primary">Languages</h3>
            <p className="text-sm text-content-secondary">
              Configure the languages available when creating pipelines.
            </p>
          </div>
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
                      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
                        language.is_active ? 'bg-accent' : 'bg-border-strong'
                      }`}
                      title={language.is_active ? 'Disable language' : 'Enable language'}
                    >
                      <span
                        className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                          language.is_active ? 'translate-x-5' : 'translate-x-0'
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
      </>
      )}
    </div>
  );
};

export default Settings;
