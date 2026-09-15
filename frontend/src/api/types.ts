export interface AccountConfig {
  url?: string;
  username?: string;
  password?: string;
  app_password?: string;
  api_key?: string;
  base_url?: string;
  text_model?: string;
  fallback_text_model?: string;
  image_model?: string;
  page_id?: string;
  access_token?: string;
  bot_token?: string;
  chat_id?: string;
}

export interface Account {
  id: string;
  name: string;
  type: "wp" | "ai" | "fb" | "tg";
  config: AccountConfig;
}

export interface AIModel {
  id: string;
  name?: string;
  owned_by?: string;
  context_length?: number;
  type?: string;
}

export interface Pipeline {
  id: string;
  name: string;
  type: string;
  language: string;
  step_accounts: Record<string, string>;
  settings: {
    wp_category_id?: string;
    collect_patterns?: boolean;
  };
  wp_category_id?: string;
  is_active: boolean;
}

export interface Language {
  code: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AppSettings {
  translation_mode: "sequential" | "parallel";
  translation_max_concurrency: number;
  ai_request_timeout: number;
  translation_chunk_size: number;
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
  workflow_type?: string;
  parent_job_id?: string | null;
  draft_id?: string | null;
  capabilities?: {
    can_cancel: boolean;
    can_rerun: boolean;
    can_open_draft: boolean;
    can_copy_link: boolean;
  };
}

export interface JobPage {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ContentDraft {
  id: string;
  pipeline_id?: string | null;
  wp_account_id?: string | null;
  kind: 'rewrite' | 'generated' | 'manual';
  source_url?: string | null;
  language?: string | null;
  title: string;
  content: string;
  caption?: string | null;
  image_kind?: 'upload' | 'url' | null;
  image_source?: string | null;
  content_format: 'plain' | 'html';
  category_id?: string | null;
  wp_status: 'draft' | 'publish';
  state: string;
  error?: string | null;
  version: number;
  wp_post_id?: string | null;
  wp_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatternArticle {
  id: string;
  source_url: string;
  original_title: string;
  theme_tags: string[];
  structure?: Record<string, unknown> | null;
  word_count: number;
  analysis_status: string;
  analysis_error?: string | null;
  processed_at: string;
  updated_at: string;
}

export interface ThemeRule {
  id: string;
  tag: string;
  keywords: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
