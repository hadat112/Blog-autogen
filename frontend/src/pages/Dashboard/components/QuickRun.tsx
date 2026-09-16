import React, { useEffect, useRef, useState } from 'react';
import { Send, Zap, WandSparkles } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getPipelines, getSettings } from '../../../api/client';
import { startArticleWorkflow } from '../../../api/workflows';
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
  const [useProxy, setUseProxy] = useState(() => window.localStorage.getItem('story-autogen-source-proxy') === 'true');

  useEffect(() => {
    window.localStorage.setItem('story-autogen-workflow-version', version);
  }, [version]);
  useEffect(() => {
    window.localStorage.setItem('story-autogen-source-proxy', String(useProxy));
  }, [useProxy]);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const { data } = await getPipelines(true);
      return data;
    },
  });
  const { data: appSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await getSettings()).data,
  });
  const proxyConfigured = Boolean(appSettings?.proxy_url?.trim());

  useEffect(() => {
    if (appSettings && !proxyConfigured && useProxy) {
      setUseProxy(false);
    }
  }, [appSettings, proxyConfigured, useProxy]);

  const availablePipelines = pipelines.filter(
    pipeline => Boolean(pipeline.step_accounts?.ai) && Boolean(pipeline.step_accounts?.wp)
  );

  useEffect(() => {
    if (availablePipelines.length > 0 && !availablePipelines.some(pipeline => pipeline.id === selectedPipeline)) {
      setSelectedPipeline(availablePipelines[0].id);
    }
  }, [availablePipelines, selectedPipeline]);

  const runMutation = useMutation({
    mutationFn: (data: { pipelineId: string; sourceUrl: string; useProxy: boolean }) =>
      startArticleWorkflow(data.pipelineId, data.sourceUrl, version, data.useProxy),
    onSuccess: (response) => {
      setInput('');
      if (onRunStarted) onRunStarted(response.data.job_id);
    },
    onError: (error: any) => {
      alert('Failed to start workflow: ' + (error.response?.data?.detail || error.message));
    },
  });

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!selectedPipeline || !trimmed) return;
    if (!/^https?:\/\//i.test(trimmed)) {
      alert('Please enter a valid HTTP or HTTPS article URL.');
      return;
    }
    if (useProxy && !proxyConfigured) {
      alert('Configure a proxy URL in Settings before enabling Proxy.');
      return;
    }
    runMutation.mutate({ pipelineId: selectedPipeline, sourceUrl: trimmed, useProxy });
  };

  const handlePipelineChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPipeline(e.target.value);
    inputRef.current?.focus();
  };

  const handleProxyToggle = () => {
    if (!proxyConfigured) {
      alert('No valid proxy is configured. Open Settings and configure a proxy first.');
      return;
    }
    setUseProxy(value => !value);
  };

  return (
    <Card className="border-border-default shadow-sm overflow-hidden">
      <CardHeader className="flex-row items-center justify-between gap-3 p-5 pb-0">
        <CardTitle className="flex min-w-0 items-center space-x-2 text-base font-bold text-content-primary">
          <div className="shrink-0 rounded-md bg-accent/10 p-1.5 text-accent">
            <Zap size={16} fill="currentColor" />
          </div>
          <span>Run workflow</span>
        </CardTitle>
        <div className="flex shrink-0 items-center gap-2">
          <div className="flex h-7 rounded-md border border-border-default bg-surface-subtle p-0.5" role="group" aria-label="Version">
            {(['v1', 'v2'] as const).map(option => (
              <button
                key={option}
                type="button"
                aria-pressed={version === option}
                onClick={() => setVersion(option)}
                className={`min-w-10 rounded px-2 text-[10px] font-bold transition-colors ${version === option ? 'bg-surface text-accent shadow-sm' : 'text-content-tertiary hover:text-content-primary'}`}
              >
                {option.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={useProxy}
            aria-disabled={!proxyConfigured}
            onClick={handleProxyToggle}
            className={`flex h-7 items-center gap-1.5 rounded-md border px-2 text-[10px] font-bold transition-colors ${!proxyConfigured ? 'cursor-not-allowed border-border-default bg-surface-subtle text-content-tertiary opacity-60' : useProxy ? 'border-accent/40 bg-accent/10 text-accent' : 'border-border-default bg-surface-subtle text-content-tertiary'}`}
            title={proxyConfigured ? 'Toggle source proxy' : 'Configure a proxy in Settings first'}
          >
              <span className={`relative h-3.5 w-6 rounded-full transition-colors ${useProxy ? 'bg-accent' : 'bg-border-strong'}`}>
                <span className={`absolute left-0.5 top-0.5 h-2.5 w-2.5 rounded-full bg-white shadow transition-transform ${useProxy ? 'translate-x-2.5' : 'translate-x-0'}`} />
            </span>
            {useProxy ? 'Proxy ON' : 'Proxy OFF'}
          </button>
        </div>
      </CardHeader>
      
      <CardContent className="p-5">
        <form onSubmit={handleRun} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="w-full space-y-1.5 md:w-52 md:flex-none">
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
              {availablePipelines.length === 0 && <option value="">No AI + WP pipeline found</option>}
            </Select>
          </div>
          
          <div className="flex-[2] w-full space-y-1.5">
            <label className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Source Article URL</label>
            <div className="relative group">
              <Input 
                ref={inputRef}
                size="default"
                className="pr-12 bg-surface-subtle focus:bg-surface transition-all border-border-default group-hover:border-accent/50"
                placeholder="Paste an article URL (https://...)..."
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
