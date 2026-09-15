import React, { useEffect, useRef, useState } from 'react';
import { Send, Zap, WandSparkles } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getPipelines, runPipeline } from '../../../api/client';
import { startRewrite } from '../../../api/workflows';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';

interface QuickRunProps {
  onRunStarted?: (jobId: string) => void;
}

const QuickRun: React.FC<QuickRunProps> = ({ onRunStarted }) => {
  const [selectedPipeline, setSelectedPipeline] = useState('');
  const [input, setInput] = useState('');
  const [version, setVersion] = useState<'v1' | 'v2'>(() => {
    const saved = window.localStorage.getItem('story-autogen-workflow-version');
    return saved === 'v2' ? 'v2' : 'v1';
  });

  useEffect(() => {
    window.localStorage.setItem('story-autogen-workflow-version', version);
  }, [version]);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const { data } = await getPipelines(true);
      return data;
    },
  });

  const availablePipelines = version === 'v2'
    ? pipelines.filter(pipeline => Boolean(pipeline.step_accounts?.ai) && Boolean(pipeline.step_accounts?.wp))
    : pipelines;

  useEffect(() => {
    if (availablePipelines.length > 0 && !availablePipelines.some(pipeline => pipeline.id === selectedPipeline)) {
      setSelectedPipeline(availablePipelines[0].id);
    }
  }, [availablePipelines, selectedPipeline]);

  const runMutation = useMutation({
    mutationFn: (data: { pipelineId: string; prompt: string }) =>
      version === 'v2'
        ? startRewrite(data.pipelineId, data.prompt)
        : runPipeline(data.pipelineId, { prompt: data.prompt }),
    onSuccess: (response) => {
      setInput('');
      if (onRunStarted) onRunStarted(response.data.job_id);
    },
    onError: (error: any) => {
      alert('Failed to start pipeline: ' + (error.response?.data?.detail || error.message));
    },
  });

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPipeline || !input.trim()) return;
    runMutation.mutate({ pipelineId: selectedPipeline, prompt: input.trim() });
  };

  const handlePipelineChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPipeline(e.target.value);
    inputRef.current?.focus();
  };

  return (
    <Card className="border-border-default shadow-sm overflow-hidden">
      <CardHeader className="p-5 pb-0">
        <CardTitle className="text-base font-bold flex items-center space-x-2 text-content-primary">
          <div className="p-1.5 bg-accent/10 text-accent rounded-md">
            <Zap size={16} fill="currentColor" />
          </div>
          <span>Run workflow</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="p-5">
        <form onSubmit={handleRun} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="w-full space-y-1.5 md:w-auto">
            <span className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Version</span>
            <div className="flex h-9 rounded-md border border-border-default bg-surface-subtle p-0.5" role="group" aria-label="Version">
              {(['v1', 'v2'] as const).map(option => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={version === option}
                  onClick={() => setVersion(option)}
                  className={`min-w-12 rounded px-2 text-xs font-bold transition-colors ${version === option ? 'bg-surface text-accent shadow-sm' : 'text-content-tertiary hover:text-content-primary'}`}
                >
                  {option.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 w-full space-y-1.5">
            <label className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Select Pipeline</label>
            <Select 
              size="default"
              className="bg-surface-subtle focus:bg-surface transition-colors border-border-default"
              value={selectedPipeline}
              onChange={handlePipelineChange}
            >
              {availablePipelines.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.language})</option>
              ))}
              {availablePipelines.length === 0 && <option value="">{version === 'v2' ? 'No AI + WP pipeline found' : 'No pipelines found'}</option>}
            </Select>
          </div>
          
          <div className="flex-[2] w-full space-y-1.5">
            <label className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Content Input (URL / Prompt)</label>
            <div className="relative group">
              <Input 
                ref={inputRef}
                size="default"
                className="pr-12 bg-surface-subtle focus:bg-surface transition-all border-border-default group-hover:border-accent/50"
                placeholder="Paste an article URL or enter a creative prompt..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={runMutation.isPending}
              />
              <Button 
                type="submit"
                disabled={runMutation.isPending || !input.trim() || !selectedPipeline}
                className="absolute right-1 top-1 bottom-1 h-7 px-3 shadow-none"
                size="sm"
              >
                {runMutation.isPending ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  <>
                    {version === 'v2' ? <WandSparkles size={14} className="mr-1.5" /> : <Send size={14} className="mr-1.5" />}
                    <span className="text-xs font-bold">Run</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default QuickRun;
