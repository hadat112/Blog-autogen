import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  Eye,
  EyeOff,
  FlaskConical,
  Loader2,
  Play,
  Star,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import {
  createTranslationBenchmark,
  getAccounts,
  getTranslationBenchmark,
  getTranslationBenchmarks,
  rateTranslationBenchmark,
} from "../../api/client";
import {
  TranslationBenchmarkCandidate,
  TranslationBenchmarkRun,
} from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

const LANGUAGES = [
  "Italian",
  "Croatian",
  "Polish",
  "Romanian",
  "Lithuanian",
  "Ukrainian",
  "Vietnamese",
  "English",
];

const formatDuration = (milliseconds: number) => {
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
};

const TranslationBenchmarks: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [targetLanguage, setTargetLanguage] = useState("Italian");
  const [suite, setSuite] = useState<"standard" | "custom">("standard");
  const [customTitle, setCustomTitle] = useState("");
  const [customContent, setCustomContent] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [revealModels, setRevealModels] = useState(false);
  const [expandedCandidate, setExpandedCandidate] = useState<string | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await getAccounts()).data,
  });
  const aiAccounts = accounts.filter((account) => account.type === "ai");

  const { data: runs = [] } = useQuery({
    queryKey: ["translation-benchmarks"],
    queryFn: async () => (await getTranslationBenchmarks()).data,
    refetchInterval: 4000,
  });

  useEffect(() => {
    if (!selectedRunId && runs.length > 0) setSelectedRunId(runs[0].id);
  }, [runs, selectedRunId]);

  const selectedListRun = runs.find((run) => run.id === selectedRunId);
  const shouldPoll = selectedListRun?.status === "queued" || selectedListRun?.status === "running";
  const { data: selectedRun } = useQuery({
    queryKey: ["translation-benchmark", selectedRunId],
    queryFn: async () => (await getTranslationBenchmark(selectedRunId!)).data,
    enabled: Boolean(selectedRunId),
    refetchInterval: shouldPoll ? 2000 : false,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createTranslationBenchmark({
        account_ids: selectedAccounts,
        target_language: targetLanguage,
        suite,
        custom_title: suite === "custom" ? customTitle : undefined,
        custom_content: suite === "custom" ? customContent : undefined,
      }),
    onSuccess: ({ data }) => {
      setSelectedRunId(data.id);
      setRevealModels(false);
      queryClient.invalidateQueries({ queryKey: ["translation-benchmarks"] });
    },
  });

  const ratingMutation = useMutation({
    mutationFn: ({
      runId,
      accountId,
      score,
    }: {
      runId: string;
      accountId: string;
      score: number;
    }) => rateTranslationBenchmark(runId, { account_id: accountId, score }),
    onSuccess: ({ data }) => {
      queryClient.setQueryData(["translation-benchmark", data.id], data);
      queryClient.invalidateQueries({ queryKey: ["translation-benchmarks"] });
    },
  });

  const canRun =
    selectedAccounts.length >= 2 &&
    (suite === "standard" || customContent.trim().length > 0) &&
    !createMutation.isPending;

  const results = useMemo(
    () => (selectedRun?.results || []).slice().sort((a, b) => b.average_score - a.average_score),
    [selectedRun],
  );

  const toggleAccount = (accountId: string) => {
    setSelectedAccounts((current) =>
      current.includes(accountId)
        ? current.filter((id) => id !== accountId)
        : [...current, accountId],
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-accent/10 p-2 text-accent">
            <FlaskConical size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-content-primary">Translation Benchmark</h2>
            <p className="text-sm text-content-secondary">
              Compare configured AI models with identical prompts, inputs, and one attempt per request.
            </p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New benchmark</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-content-primary">
              Models to compare
            </label>
            {aiAccounts.length < 2 ? (
              <div className="rounded-lg border border-warning/30 bg-warning/5 p-4 text-sm text-content-secondary">
                Create at least two AI accounts before running a benchmark.
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {aiAccounts.map((account) => {
                  const checked = selectedAccounts.includes(account.id);
                  return (
                    <button
                      type="button"
                      key={account.id}
                      onClick={() => toggleAccount(account.id)}
                      className={`rounded-lg border p-4 text-left transition-colors ${
                        checked
                          ? "border-accent bg-accent/5"
                          : "border-border-default hover:bg-surface-subtle"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-content-primary">{account.name}</div>
                          <div className="mt-1 text-xs text-content-tertiary">
                            {account.config.text_model || "No text model"}
                          </div>
                        </div>
                        <div
                          className={`mt-1 h-4 w-4 rounded border ${
                            checked ? "border-accent bg-accent" : "border-border-default"
                          }`}
                        />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-content-primary">
                Target language
              </label>
              <Select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}>
                {LANGUAGES.map((language) => (
                  <option value={language} key={language}>{language}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-content-primary">
                Test suite
              </label>
              <Select
                value={suite}
                onChange={(event) => setSuite(event.target.value as "standard" | "custom")}
              >
                <option value="standard">Standard suite (3 cases)</option>
                <option value="custom">Custom article</option>
              </Select>
            </div>
          </div>

          {suite === "custom" && (
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-content-primary">
                  Source title
                </label>
                <Input
                  value={customTitle}
                  onChange={(event) => setCustomTitle(event.target.value)}
                  placeholder="Article title"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-content-primary">
                  Source content
                </label>
                <textarea
                  value={customContent}
                  onChange={(event) => setCustomContent(event.target.value)}
                  rows={10}
                  placeholder="Paste the source article here..."
                  className="w-full rounded-lg border border-border-default bg-surface px-3 py-2 text-sm text-content-primary outline-none focus:border-accent"
                />
              </div>
            </div>
          )}

          {createMutation.isError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-600">
              {(createMutation.error as any)?.response?.data?.detail ||
                (createMutation.error as Error).message}
            </div>
          )}

          <div className="flex items-center justify-between gap-4">
            <p className="text-xs text-content-tertiary">
              Selected: {selectedAccounts.length}. Each model processes the same cases independently.
            </p>
            <Button onClick={() => createMutation.mutate()} disabled={!canRun}>
              {createMutation.isPending ? (
                <Loader2 className="mr-2 animate-spin" size={16} />
              ) : (
                <Play className="mr-2" size={16} />
              )}
              Run benchmark
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[260px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Benchmark history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {runs.length === 0 ? (
              <p className="text-sm text-content-tertiary">No benchmark runs yet.</p>
            ) : (
              runs.map((run) => (
                <button
                  type="button"
                  key={run.id}
                  onClick={() => {
                    setSelectedRunId(run.id);
                    setRevealModels(false);
                  }}
                  className={`w-full rounded-lg border p-3 text-left ${
                    selectedRunId === run.id
                      ? "border-accent bg-accent/5"
                      : "border-border-default"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-content-primary">
                      {run.target_language}
                    </span>
                    <span className="text-xs capitalize text-content-tertiary">{run.status}</span>
                  </div>
                  <div className="mt-1 text-xs text-content-tertiary">
                    {run.selected_account_ids.length} models · {run.suite}
                  </div>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {selectedRun && (
            <>
              {(selectedRun.status === "queued" || selectedRun.status === "running") && (
                <Card>
                  <CardContent className="py-6">
                    <div className="mb-3 flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 font-medium text-content-primary">
                        <Loader2 className="animate-spin text-accent" size={16} />
                        {selectedRun.current_step || "Running benchmark"}
                      </span>
                      <span className="text-content-secondary">{selectedRun.progress}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-surface-subtle">
                      <div
                        className="h-full bg-accent transition-all"
                        style={{ width: `${selectedRun.progress}%` }}
                      />
                    </div>
                  </CardContent>
                </Card>
              )}

              {selectedRun.status === "failed" && (
                <Card>
                  <CardContent className="flex gap-3 py-6 text-red-600">
                    <AlertTriangle size={20} />
                    <span>{selectedRun.error || "Benchmark failed"}</span>
                  </CardContent>
                </Card>
              )}

              {results.length > 0 && (
                <>
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between gap-4">
                        <CardTitle>Results</CardTitle>
                        <Button variant="secondary" onClick={() => setRevealModels((value) => !value)}>
                          {revealModels ? <EyeOff className="mr-2" size={16} /> : <Eye className="mr-2" size={16} />}
                          {revealModels ? "Hide models" : "Reveal models"}
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[760px] text-left text-sm">
                          <thead className="border-b border-border-default text-content-tertiary">
                            <tr>
                              <th className="pb-3">Candidate</th>
                              <th className="pb-3">Hard score</th>
                              <th className="pb-3">Valid rate</th>
                              <th className="pb-3">Latency</th>
                              <th className="pb-3">Requests</th>
                              <th className="pb-3">Tokens</th>
                              <th className="pb-3">Manual rating</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results.map((candidate, index) => (
                              <tr key={candidate.account_id} className="border-b border-border-subtle">
                                <td className="py-4">
                                  <div className="font-semibold text-content-primary">
                                    #{index + 1} {candidate.blind_label}
                                  </div>
                                  {revealModels && (
                                    <div className="text-xs text-content-tertiary">
                                      {candidate.account_name} · {candidate.model}
                                    </div>
                                  )}
                                </td>
                                <td className="py-4 font-semibold text-content-primary">
                                  {candidate.average_score}
                                </td>
                                <td className="py-4">
                                  <span className="flex items-center gap-1">
                                    {candidate.valid_rate === 1 ? (
                                      <CheckCircle2 size={15} className="text-green-600" />
                                    ) : (
                                      <AlertTriangle size={15} className="text-amber-600" />
                                    )}
                                    {Math.round(candidate.valid_rate * 100)}%
                                  </span>
                                </td>
                                <td className="py-4">{formatDuration(candidate.latency_ms)}</td>
                                <td className="py-4">{candidate.request_count}</td>
                                <td className="py-4">
                                  {candidate.input_tokens + candidate.output_tokens || "N/A"}
                                </td>
                                <td className="py-4">
                                  <div className="flex gap-1">
                                    {[1, 2, 3, 4, 5].map((score) => {
                                      const selected =
                                        (selectedRun.manual_ratings[candidate.account_id]?.score || 0) >= score;
                                      return (
                                        <button
                                          type="button"
                                          key={score}
                                          onClick={() =>
                                            ratingMutation.mutate({
                                              runId: selectedRun.id,
                                              accountId: candidate.account_id,
                                              score,
                                            })
                                          }
                                          title={`${score}/5`}
                                        >
                                          <Star
                                            size={16}
                                            className={selected ? "fill-amber-400 text-amber-400" : "text-content-tertiary"}
                                          />
                                        </button>
                                      );
                                    })}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="mt-4 text-xs text-content-tertiary">
                        Hard score checks structure, numbers, length, refusals, and source leakage. It does not judge fluency or semantic nuance; use blind manual ratings for that.
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Blind output review</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {results.map((candidate) => (
                        <CandidateOutput
                          key={candidate.account_id}
                          candidate={candidate}
                          revealModels={revealModels}
                          expanded={expandedCandidate === candidate.account_id}
                          onToggle={() =>
                            setExpandedCandidate((current) =>
                              current === candidate.account_id ? null : candidate.account_id,
                            )
                          }
                        />
                      ))}
                    </CardContent>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const CandidateOutput = ({
  candidate,
  revealModels,
  expanded,
  onToggle,
}: {
  candidate: TranslationBenchmarkCandidate;
  revealModels: boolean;
  expanded: boolean;
  onToggle: () => void;
}) => (
  <div className="rounded-lg border border-border-default">
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between gap-4 p-4 text-left"
    >
      <div>
        <div className="font-semibold text-content-primary">{candidate.blind_label}</div>
        {revealModels && (
          <div className="text-xs text-content-tertiary">
            {candidate.account_name} · {candidate.model}
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 text-sm text-content-secondary">
        <span className="flex items-center gap-1">
          <Clock3 size={14} />
          {formatDuration(candidate.latency_ms)}
        </span>
        {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </div>
    </button>
    {expanded && (
      <div className="space-y-5 border-t border-border-default p-4">
        {candidate.cases.map((caseResult) => (
          <div key={caseResult.case_id} className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-lg bg-surface-subtle p-4">
              <div className="mb-2 text-xs font-bold uppercase tracking-wide text-content-tertiary">
                Source · {caseResult.case_id}
              </div>
              <h4 className="font-semibold text-content-primary">{caseResult.source_title}</h4>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-content-secondary">
                {caseResult.source_content}
              </p>
            </div>
            <div className="rounded-lg bg-surface-subtle p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wide text-content-tertiary">
                  Translation
                </span>
                <span className="text-xs font-semibold text-content-secondary">
                  Score {caseResult.score}
                </span>
              </div>
              {caseResult.error ? (
                <p className="text-sm text-red-600">{caseResult.error}</p>
              ) : (
                <>
                  <h4 className="font-semibold text-content-primary">
                    {caseResult.translated_title}
                  </h4>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-content-secondary">
                    {caseResult.translated_content}
                  </p>
                  {(caseResult.content_metrics?.warnings || []).length > 0 && (
                    <div className="mt-4 space-y-1 text-xs text-amber-700">
                      {caseResult.content_metrics?.warnings.map((warning: string) => (
                        <div key={warning}>• {warning}</div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default TranslationBenchmarks;
