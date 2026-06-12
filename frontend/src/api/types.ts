export interface AccountConfig {
  url?: string;
  username?: string;
  password?: string;
  app_password?: string;
  api_key?: string;
  base_url?: string;
  text_model?: string;
  image_model?: string;
  translation_chunk_size?: string;
  translation_context_chars?: string;
  page_id?: string;
  access_token?: string;
  spreadsheet_id?: string;
  credentials_path?: string;
  bot_token?: string;
  chat_id?: string;
}

export interface Account {
  id: string;
  name: string;
  type: "wp" | "ai" | "fb" | "gs" | "tg";
  config: AccountConfig;
}

export interface Pipeline {
  id: string;
  name: string;
  type: string;
  language: string;
  step_accounts: Record<string, string>;
  settings: {
    wp_category_id?: string;
  };
  wp_category_id?: string;
  is_active: boolean;
}

export interface Job {
  id: string;
  pipeline_id: string;
  pipeline_name?: string;
  input_text?: string | null;
  input_type?: "url" | "prompt" | null;
  status: "queued" | "pending" | "running" | "success" | "partial_success" | "failed" | "cancelled";
  current_step?: string;
  progress: number;
  logs?: any[];
  start_time: string;
  end_time?: string | null;
  rerun_at?: string | null;
  rerun_job_id?: string | null;
  title?: string;
  url?: string;
  error?: string;
  created_at?: string;
  updated_at?: string;
  outputs?: Record<string, any>;
}

export interface TranslationBenchmarkCaseResult {
  case_id: string;
  source_title: string;
  source_content: string;
  translated_title: string;
  translated_content: string;
  score: number;
  valid: boolean;
  latency_ms: number;
  error?: string | null;
  title_metrics?: Record<string, any> | null;
  content_metrics?: Record<string, any> | null;
}

export interface TranslationBenchmarkCandidate {
  account_id: string;
  account_name: string;
  model: string;
  blind_label: string;
  average_score: number;
  valid_rate: number;
  latency_ms: number;
  request_count: number;
  input_tokens: number;
  output_tokens: number;
  cases: TranslationBenchmarkCaseResult[];
}

export interface TranslationBenchmarkRun {
  id: string;
  status: "queued" | "running" | "success" | "failed";
  progress: number;
  current_step?: string | null;
  target_language: string;
  suite: "standard" | "custom";
  selected_account_ids: string[];
  request_config: {
    suite?: string;
    custom_title?: string;
    custom_content?: string;
  };
  results: TranslationBenchmarkCandidate[];
  manual_ratings: Record<string, { score: number; notes?: string }>;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}
