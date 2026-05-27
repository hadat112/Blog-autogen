import { CheckCircle, RefreshCw, Search, X, XCircle } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getWPCategories, testAccount } from "../../../api/client";
import { Account, AccountConfig } from "../../../api/types";
import { Button } from "../../../components/ui/Button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { cn } from "../../../lib/utils";

interface AccountFormProps {
  account: Account | null;
  onClose: () => void;
  onSave: (formData: Partial<Account>) => void;
}

const AccountForm: React.FC<AccountFormProps> = ({
  account,
  onClose,
  onSave,
}) => {
  const [formData, setFormData] = useState<Partial<Account>>({
    name: "",
    type: "wp",
    config: {},
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [fetchingCats, setFetchingCats] = useState(false);

  useEffect(() => {
    if (account) {
      setFormData(account);
    }
  }, [account]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const testData = {
        type: formData.type,
        config: formData.config as AccountConfig,
      };
      await testAccount(testData);
      setTestResult({
        success: true,
        message: "Connection verified successfully!",
      });
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || "Connection test failed.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleFetchCategories = async () => {
    if (!formData.config?.url) return;
    setFetchingCats(true);
    try {
      const { data } = await getWPCategories(formData.config as AccountConfig);
      setCategories(data);
    } catch (error: any) {
      alert(
        "Failed to fetch categories: " +
          (error.response?.data?.detail || error.message),
      );
    } finally {
      setFetchingCats(false);
    }
  };

  const handleConfigChange = (key: keyof AccountConfig, value: string) => {
    setFormData({
      ...formData,
      config: {
        ...(formData.config || {}),
        [key]: value,
      },
    });
  };

  const renderConfigFields = () => {
    switch (formData.type) {
      case "wp":
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                WordPress URL
              </label>
              <Input
                type="url"
                required
                value={formData.config?.url || ""}
                onChange={(e) => handleConfigChange("url", e.target.value)}
                placeholder="https://yourblog.com"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Username
              </label>
              <Input
                type="text"
                required
                value={formData.config?.username || ""}
                onChange={(e) => handleConfigChange("username", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Application Password
              </label>
              <Input
                type="password"
                required
                value={formData.config?.password || ""}
                onChange={(e) => handleConfigChange("password", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Default Category
              </label>
              <div className="flex space-x-2">
                {categories.length > 0 ? (
                  <Select
                    className="flex-1"
                    value={formData.config?.category_id || ""}
                    onChange={(e) =>
                      handleConfigChange("category_id" as any, e.target.value)
                    }
                  >
                    <option value="">-- Use Default --</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name} ({cat.count})
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input
                    type="number"
                    className="flex-1"
                    value={formData.config?.category_id || ""}
                    onChange={(e) =>
                      handleConfigChange("category_id" as any, e.target.value)
                    }
                    placeholder="e.g. 1"
                  />
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleFetchCategories}
                  disabled={fetchingCats || !formData.config?.url}
                  title="Fetch Categories from site"
                >
                  {fetchingCats ? (
                    <RefreshCw size={16} className="animate-spin" />
                  ) : (
                    <Search size={16} />
                  )}
                </Button>
              </div>
            </div>
          </>
        );
      case "ai":
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                9router API Key
              </label>
              <Input
                type="password"
                required
                value={formData.config?.api_key || ""}
                onChange={(e) => handleConfigChange("api_key", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Base URL
              </label>
              <Input
                type="url"
                required
                value={formData.config?.base_url || "http://localhost:20128/v1"}
                onChange={(e) => handleConfigChange("base_url", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Text Model
              </label>
              <Input
                type="text"
                required
                value={formData.config?.text_model || "gpt-4o"}
                onChange={(e) =>
                  handleConfigChange("text_model", e.target.value)
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Image Model
              </label>
              <Input
                type="text"
                required
                value={formData.config?.image_model || "dall-e-3"}
                onChange={(e) =>
                  handleConfigChange("image_model", e.target.value)
                }
              />
            </div>
          </>
        );
      case "fb":
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Page ID
              </label>
              <Input
                type="text"
                required
                value={formData.config?.page_id || ""}
                onChange={(e) => handleConfigChange("page_id", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Access Token
              </label>
              <Input
                type="password"
                required
                value={formData.config?.access_token || ""}
                onChange={(e) =>
                  handleConfigChange("access_token", e.target.value)
                }
              />
            </div>
          </>
        );
      case "gs":
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Spreadsheet ID
              </label>
              <Input
                type="text"
                required
                value={formData.config?.spreadsheet_id || ""}
                onChange={(e) =>
                  handleConfigChange("spreadsheet_id", e.target.value)
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Credentials JSON Path
              </label>
              <Input
                type="text"
                required
                value={
                  (formData.config?.credentials_path as any) ||
                  "credentials.json"
                }
                onChange={(e) =>
                  handleConfigChange("credentials_path" as any, e.target.value)
                }
              />
            </div>
          </>
        );
      case "tg":
        return (
          <>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Bot Token
              </label>
              <Input
                type="password"
                required
                value={formData.config?.bot_token || ""}
                onChange={(e) =>
                  handleConfigChange("bot_token", e.target.value)
                }
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Chat ID
              </label>
              <Input
                type="text"
                required
                value={formData.config?.chat_id || ""}
                onChange={(e) => handleConfigChange("chat_id", e.target.value)}
              />
            </div>
          </>
        );
      default:
        return (
          <p className="text-sm text-content-secondary">
            Select an account type to configure
          </p>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md overflow-hidden shadow-xl border-none">
        <CardHeader className="flex flex-row justify-between items-center border-b border-border-subtle p-6">
          <CardTitle className="text-xl">
            {account ? "Edit Account" : "Add New Account"}
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="text-content-tertiary"
          >
            <X size={24} />
          </Button>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="p-6 space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Account Name
              </label>
              <Input
                type="text"
                required
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g. My WordPress Blog"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-content-primary">
                Service Type
              </label>
              <Select
                value={formData.type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    type: e.target.value as any,
                    config: {},
                  })
                }
              >
                <option value="wp">WordPress</option>
                <option value="fb">Facebook Page</option>
                <option value="ai">AI (9router)</option>
                <option value="gs">Google Sheets</option>
                <option value="tg">Telegram</option>
              </Select>
            </div>

            <div className="pt-4 border-t border-border-subtle space-y-4">
              {renderConfigFields()}
            </div>
          </CardContent>

          <CardFooter className="p-6 border-t border-border-subtle flex flex-col space-y-3">
            {testResult && (
              <div
                className={`w-full p-3 rounded-lg text-sm flex items-start space-x-2 ${
                  testResult.success
                    ? "bg-status-success/10 text-status-success border border-status-success/20"
                    : "bg-status-danger/10 text-status-danger border border-status-danger/20"
                }`}
              >
                {testResult.success ? (
                  <CheckCircle size={18} className="mt-0.5" />
                ) : (
                  <XCircle size={18} className="mt-0.5" />
                )}
                <span>{testResult.message}</span>
              </div>
            )}

            <div className="flex justify-between items-center w-full pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={handleTest}
                disabled={testing}
                className="text-accent hover:bg-canvas"
              >
                <RefreshCw
                  size={18}
                  className={cn("mr-2", testing && "animate-spin")}
                />
                Test Connection
              </Button>

              <div className="flex space-x-3">
                <Button variant="ghost" type="button" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit">{account ? "Update" : "Create"}</Button>
              </div>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

export default AccountForm;
