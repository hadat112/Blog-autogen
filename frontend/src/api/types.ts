export interface AccountConfig {
  url?: string;
  username?: string;
  password?: string;
  app_password?: string;
  api_key?: string;
  base_url?: string;
  text_model?: string;
  image_model?: string;
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
