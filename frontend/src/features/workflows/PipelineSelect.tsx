import { useQuery } from '@tanstack/react-query';
import { getPipelines } from '../../api/client';
import { Select } from '../../components/ui/Select';

interface Props {
  value: string;
  onChange: (id: string) => void;
  requiresAI?: boolean;
  requiresWP?: boolean;
}

export function PipelineSelect({ value, onChange, requiresAI = false, requiresWP = false }: Props) {
  const pipelines = useQuery({
    queryKey: ['pipelines', 'available'],
    queryFn: async () => (await getPipelines(true)).data,
  });
  const available = (pipelines.data ?? []).filter(pipeline => {
    const accounts = pipeline.step_accounts ?? {};
    return (!requiresAI || Boolean(accounts.ai)) && (!requiresWP || Boolean(accounts.wp));
  });

  return (
    <label className="block text-sm font-medium text-content-primary">
      Pipeline
      <Select className="mt-1" value={value} onChange={event => onChange(event.target.value)} disabled={pipelines.isLoading}>
        <option value="">{pipelines.isLoading ? 'Loading pipelines…' : available.length ? 'Select a pipeline' : 'No matching pipeline found'}</option>
        {available.map(pipeline => <option key={pipeline.id} value={pipeline.id}>{pipeline.name}{pipeline.language ? ` (${pipeline.language})` : ''}</option>)}
      </Select>
    </label>
  );
}
