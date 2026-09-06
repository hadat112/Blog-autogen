import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Pencil, Plus, Save, Trash2, X } from 'lucide-react';
import { getAccounts, getLanguages } from '../../api/client';
import { createWorkflowProfile, deleteWorkflowProfile, getWorkflowCategories, getWorkflowProfiles, updateWorkflowProfile } from '../../api/workflows';
import type { WorkflowProfile, WorkflowType } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { InlineStatus } from '../../components/ui/InlineStatus';

interface Props {
  type: WorkflowType;
  value: string;
  onChange: (id: string) => void;
}

const labels: Record<WorkflowType, string> = {
  rewrite: 'Rewrite',
  generate_story: 'Generate Story',
  wp_publish: 'WordPress Publisher',
};

export function ProfileManager({ type, value, onChange }: Props) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [language, setLanguage] = useState('');
  const [aiId, setAiId] = useState('');
  const [wpId, setWpId] = useState('');
  const [category, setCategory] = useState('');
  const [collectPatterns, setCollectPatterns] = useState(false);
  const [error, setError] = useState('');

  const profilesQuery = useQuery({
    queryKey: ['workflow-profiles', type],
    queryFn: async () => (await getWorkflowProfiles(type)).data,
  });
  const accountsQuery = useQuery({ queryKey: ['accounts'], queryFn: async () => (await getAccounts()).data });
  const languagesQuery = useQuery({ queryKey: ['languages'], queryFn: async () => (await getLanguages()).data });
  const profiles = profilesQuery.data ?? [];
  const selected = profiles.find(profile => profile.id === value);
  const categoriesQuery = useQuery({ queryKey: ['workflow-categories', selected?.id], queryFn: async () => (await getWorkflowCategories(selected!.id)).data, enabled: Boolean(selected), retry: false });

  useEffect(() => {
    if (!value && profiles[0]) onChange(profiles[0].id);
  }, [profiles, value, onChange]);

  const resetForm = (profile?: WorkflowProfile) => {
    setName(profile?.name ?? '');
    setLanguage(profile?.language ?? '');
    setAiId(profile?.step_accounts.ai ?? '');
    setWpId(profile?.step_accounts.wp ?? '');
    setCategory(profile?.settings.wp_category_id ?? '');
    setCollectPatterns(Boolean(profile?.settings.collect_patterns));
    setError('');
  };

  const save = useMutation({
    mutationFn: async () => {
      if (!name.trim() || !wpId || (type !== 'wp_publish' && (!aiId || !language))) {
        throw new Error('Complete all required profile fields.');
      }
      const payload = {
        name: name.trim(), type, language: type === 'wp_publish' ? '' : language,
        step_accounts: { ...(type !== 'wp_publish' ? { ai: aiId } : {}), wp: wpId },
        settings: { wp_category_id: category || undefined, ...(type === 'rewrite' ? { collect_patterns: collectPatterns } : {}) },
        wp_category_id: category || undefined, is_active: true,
      };
      return selected && editing && !creating ? updateWorkflowProfile(selected.id, payload) : createWorkflowProfile(payload);
    },
    onSuccess: ({ data }) => {
      queryClient.invalidateQueries({ queryKey: ['workflow-profiles', type] });
      onChange(data.id);
      setEditing(false);
      setCreating(false);
      resetForm();
    },
    onError: (reason: any) => setError(reason.response?.data?.detail || reason.message || 'Could not save profile.'),
  });

  const remove = useMutation({
    mutationFn: deleteWorkflowProfile,
    onSuccess: () => {
      onChange('');
      queryClient.invalidateQueries({ queryKey: ['workflow-profiles', type] });
    },
    onError: (reason: any) => setError(reason.response?.data?.detail || 'Could not delete profile.'),
  });

  return <section className="space-y-4">
    <div className="flex items-end gap-2">
      <label className="min-w-0 flex-1 text-sm font-medium text-content-primary">
        {labels[type]} profile
        <Select className="mt-1" value={value} onChange={event => onChange(event.target.value)}>
          <option value="">Select a profile</option>
          {profiles.map(profile => <option value={profile.id} key={profile.id}>{profile.name}</option>)}
        </Select>
      </label>
      <Button type="button" variant="outline" size="icon" title="Create profile" onClick={() => { resetForm(); setCreating(true); setEditing(true); }}><Plus size={16} /></Button>
      <Button type="button" variant="outline" size="icon" title="Edit profile" disabled={!selected} onClick={() => { resetForm(selected); setCreating(false); setEditing(true); }}><Pencil size={16} /></Button>
      <Button type="button" variant="outline" size="icon" title="Delete profile" disabled={!selected || remove.isPending} onClick={() => selected && window.confirm(`Delete profile “${selected.name}”?`) && remove.mutate(selected.id)}><Trash2 size={16} /></Button>
    </div>

    {profilesQuery.isError && <InlineStatus tone="error">Could not load workflow profiles.</InlineStatus>}
    {editing && <div className="space-y-3 rounded-xl border border-border-default bg-surface-subtle p-4">
      <div className="flex items-center justify-between"><h4 className="font-semibold text-content-primary">{creating ? 'New' : 'Edit'} profile</h4><Button type="button" variant="ghost" size="icon" onClick={() => { setEditing(false); setCreating(false); }}><X size={16} /></Button></div>
      <label className="block text-sm font-medium">Name<Input className="mt-1" value={name} onChange={event => setName(event.target.value)} /></label>
      {type !== 'wp_publish' && <label className="block text-sm font-medium">Target language<Select className="mt-1" value={language} onChange={event => setLanguage(event.target.value)}><option value="">Select language</option>{(languagesQuery.data ?? []).filter(item => item.is_active || item.display_name === language).map(item => <option key={item.code} value={item.display_name}>{item.display_name}</option>)}</Select></label>}
      {type !== 'wp_publish' && <label className="block text-sm font-medium">AI Provider<Select className="mt-1" value={aiId} onChange={event => setAiId(event.target.value)}><option value="">Select AI account</option>{(accountsQuery.data ?? []).filter(item => item.type === 'ai').map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>}
      <label className="block text-sm font-medium">WordPress account<Select className="mt-1" value={wpId} onChange={event => setWpId(event.target.value)}><option value="">Select WordPress account</option>{(accountsQuery.data ?? []).filter(item => item.type === 'wp').map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
      <label className="block text-sm font-medium">Default category <span className="text-content-tertiary">(optional)</span>{selected && !creating ? <Select className="mt-1" value={category} onChange={event => setCategory(event.target.value)}><option value="">Uncategorized</option>{(categoriesQuery.data ?? []).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select> : <Input className="mt-1" value={category} onChange={event => setCategory(event.target.value)} placeholder="Save profile, then edit to load categories" />}</label>
      {type === 'rewrite' && <label className="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={collectPatterns} onChange={event => setCollectPatterns(event.target.checked)} />Collect story patterns in the background</label>}
      {error && <InlineStatus tone="error">{error}</InlineStatus>}
      <Button type="button" onClick={() => save.mutate()} disabled={save.isPending}><Save size={15} className="mr-2" />{save.isPending ? 'Saving…' : 'Save profile'}</Button>
    </div>}
  </section>;
}
