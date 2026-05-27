import React, { useState, useEffect } from 'react';
import { Play, Send, Zap } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getPipelines, runPipeline } from '../../../api/client';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Select } from '../../../components/ui/Select';
import { cn } from '../../../lib/utils';

interface QuickRunProps {
  onRunStarted?: (jobId: string) => void;
}

const QuickRun: React.FC<QuickRunProps> = ({ onRunStarted }) => {
  const [selectedPipeline, setSelectedPipeline] = useState('');
  const [input, setInput] = useState('');

  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const { data } = await getPipelines();
      return data;
    },
  });

  useEffect(() => {
    if (pipelines.length > 0 && !selectedPipeline) {
      setSelectedPipeline(pipelines[0].id);
    }
  }, [pipelines, selectedPipeline]);

  const runMutation = useMutation({
    mutationFn: (data: { pipelineId: string; prompt: string }) => 
      runPipeline(data.pipelineId, { prompt: data.prompt }),
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

  return (
    <Card className="border-border-default shadow-sm overflow-hidden">
      <CardHeader className="p-5 pb-0">
        <CardTitle className="text-base font-bold flex items-center space-x-2 text-content-primary">
          <div className="p-1.5 bg-accent/10 text-accent rounded-md">
            <Zap size={16} fill="currentColor" />
          </div>
          <span>Quick Run</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="p-5">
        <form onSubmit={handleRun} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full space-y-1.5">
            <label className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Select Pipeline</label>
            <Select 
              size="default"
              className="bg-surface-subtle focus:bg-surface transition-colors border-border-default"
              value={selectedPipeline}
              onChange={(e) => setSelectedPipeline(e.target.value)}
            >
              {pipelines.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.language})</option>
              ))}
              {pipelines.length === 0 && <option value="">No pipelines found</option>}
            </Select>
          </div>
          
          <div className="flex-[2] w-full space-y-1.5">
            <label className="text-[10px] font-bold text-content-tertiary uppercase tracking-widest ml-0.5">Content Input (URL / Prompt)</label>
            <div className="relative group">
              <Input 
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
                    <Send size={14} className="mr-1.5" />
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
