export interface AccountConfig {
  url?: string;
  username?: string;
  password?: string;
  app_password?: string;
  category_id?: string;
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
  language: string;
  step_accounts: Record<string, string>;
}

export interface Job {
  id: string;
  pipeline_id: string;
  status: "pending" | "running" | "success" | "failed";
  title?: string;
  url?: string;
  error?: string;
  created_at: string;
  updated_at: string;
  outputs?: Record<string, any>;
}
