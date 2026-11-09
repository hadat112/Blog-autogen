import type { Job } from '../api/types';

// Display names are independent of persisted engine identifiers and retry data.
export function getArticleWorkflowLabel(job: Pick<Job, 'workflow_type' | 'outputs'>): 'V1' | 'V2' | 'V3' | undefined {
  if (job.outputs?.source_kind === 'manual') return 'V2';
  if (job.workflow_type === 'rewrite' || job.workflow_type === 'article_v2') return 'V3';
  if (!job.workflow_type || job.workflow_type === 'legacy' || job.workflow_type === 'article_v1') return 'V1';
  return undefined;
}
