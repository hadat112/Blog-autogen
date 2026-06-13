import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Search, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import {
  getAccounts,
  getLanguages,
  getWPCategories,
} from "../../../api/client";
import { Account, Pipeline } from "../../../api/types";
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

interface PipelineFormProps {
  pipeline: Pipeline | null;
  onClose: () => void;
  onSave: (formData: Partial<Pipeline>) => void;
}

const defaultFormData: Partial<Pipeline> = {
  name: "",
  type: "story",
  language: "Ukrainian",
  step_accounts: {
    ai: "",
    wp: "",
    fb: "",
    gs: "",
    tg: "",
  },
  settings: {},
  is_active: true,
};

const PipelineForm: React.FC<PipelineFormProps> = ({
  pipeline,
  onClose,
  onSave,
}) => {
  const [formData, setFormData] = useState<Partial<Pipeline>>(defaultFormData);
  const [categories, setCategories] = useState<any[]>([]);
  const [fetchingCats, setFetchingCats] = useState(false);

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const { data } = await getAccounts();
      return data;
    },
  });
  const { data: languages = [], isLoading: languagesLoading } = useQuery({
    queryKey: ["languages"],
    queryFn: async () => {
      const { data } = await getLanguages();
      return Array.isArray(data) ? data : [];
    },
  });

  useEffect(() => {
    if (pipeline) {
      const wpCategoryId =
        pipeline.wp_category_id || pipeline.settings?.wp_category_id || "";
      setFormData({
        ...defaultFormData,
        ...pipeline,
        step_accounts: {
          ...(defaultFormData.step_accounts || {}),
          ...(pipeline.step_accounts || {}),
        },
        settings: {
          ...(pipeline.settings || {}),
          wp_category_id: wpCategoryId,
        },
        wp_category_id: wpCategoryId,
      });
    } else {
      setFormData(defaultFormData);
    }
    setCategories([]);
  }, [pipeline]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...formData,
      type: formData.language ? formData.type || "story" : "crawl",
    });
  };

  const handleStepAccountChange = (step: string, accId: string) => {
    setFormData({
      ...formData,
      step_accounts: {
        ...(formData.step_accounts || {}),
        [step]: accId,
      },
      settings:
        step === "wp"
          ? {
              ...(formData.settings || {}),
              wp_category_id: "",
            }
          : formData.settings,
    });
    if (step === "wp") {
      setCategories([]);
    }
  };

  const handleSettingChange = (key: string, value: string) => {
    setFormData({
      ...formData,
      settings: {
        ...(formData.settings || {}),
        [key]: value,
      },
      ...(key === "wp_category_id" ? { wp_category_id: value } : {}),
    });
  };

  const handleLanguageChange = (language: string) => {
    setFormData({
      ...formData,
      language,
      type: language ? formData.type || "story" : "crawl",
    });
  };

  const selectedWpAccount = accounts.find(
    (account: Account) => account.id === formData.step_accounts?.wp,
  );

  const fetchCategoriesForAccount = async (account: Account) => {
    setFetchingCats(true);
    try {
      const { data } = await getWPCategories(account.config);
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

  useEffect(() => {
    if (!selectedWpAccount || categories.length > 0 || fetchingCats) return;
    if (!formData.settings?.wp_category_id) return;
    fetchCategoriesForAccount(selectedWpAccount);
  }, [selectedWpAccount, formData.settings?.wp_category_id]);

  const handleFetchCategories = async () => {
    if (!selectedWpAccount) return;
    await fetchCategoriesForAccount(selectedWpAccount);
  };

  const selectableLanguages = languages.filter(
    (language) =>
      language.is_active ||
      language.display_name === formData.language ||
      language.code === formData.language,
  );
  const currentLanguageIsMissing =
    !!formData.language &&
    !languages.some((language) => language.display_name === formData.language);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl overflow-hidden shadow-xl border-none">
        <CardHeader className="flex flex-row justify-between items-center border-b border-border-subtle p-6">
          <CardTitle className="text-xl">
            {pipeline ? "Edit Pipeline" : "Create New Pipeline"}
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
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-content-primary">
                  Pipeline Name
                </label>
                <Input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="e.g. Daily News Pipeline"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-content-primary">
                  Language
                </label>
                <Select
                  value={formData.language}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  disabled={languagesLoading}
                >
                  <option value="">Không dịch / reup nguyên bản</option>
                  {currentLanguageIsMissing && (
                    <option value={formData.language}>
                      {formData.language} (legacy)
                    </option>
                  )}
                  {selectableLanguages.map((language) => (
                    <option key={language.code} value={language.display_name}>
                      {language.display_name}
                      {` (${language.code})`}
                      {!language.is_active ? " (disabled)" : ""}
                    </option>
                  ))}
                </Select>
                {!formData.language && (
                  <p className="text-xs text-content-tertiary">
                    The crawler will reuse the original WordPress title and content without AI translation.
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-bold text-sm text-content-tertiary uppercase tracking-wider">
                Step Configuration
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    AI Account (Text/Image)
                  </label>
                  <Select
                    value={formData.step_accounts?.ai || ""}
                    onChange={(e) =>
                      handleStepAccountChange("ai", e.target.value)
                    }
                  >
                    <option value="">-- Select AI --</option>
                    {accounts
                      .filter((a) => a.type === "ai")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    WordPress Account
                  </label>
                  <Select
                    value={formData.step_accounts?.wp || ""}
                    onChange={(e) =>
                      handleStepAccountChange("wp", e.target.value)
                    }
                  >
                    <option value="">-- Select WP --</option>
                    {accounts
                      .filter((a) => a.type === "wp")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    WordPress Category
                  </label>
                  <div className="flex space-x-2">
                    {categories.length > 0 ? (
                      <Select
                        className="flex-1"
                        value={formData.settings?.wp_category_id || ""}
                        onChange={(e) =>
                          handleSettingChange("wp_category_id", e.target.value)
                        }
                        disabled={!selectedWpAccount}
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
                        value={formData.settings?.wp_category_id || ""}
                        onChange={(e) =>
                          handleSettingChange("wp_category_id", e.target.value)
                        }
                        placeholder="e.g. 1"
                        disabled={!selectedWpAccount}
                      />
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleFetchCategories}
                      disabled={fetchingCats || !selectedWpAccount}
                      title="Fetch categories from selected WordPress account"
                    >
                      {fetchingCats ? (
                        <RefreshCw size={16} className="animate-spin" />
                      ) : (
                        <Search size={16} />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    Facebook Page
                  </label>
                  <Select
                    value={formData.step_accounts?.fb || ""}
                    onChange={(e) =>
                      handleStepAccountChange("fb", e.target.value)
                    }
                  >
                    <option value="">-- Select FB --</option>
                    {accounts
                      .filter((a) => a.type === "fb")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    Google Sheets (Log)
                  </label>
                  <Select
                    value={formData.step_accounts?.gs || ""}
                    onChange={(e) =>
                      handleStepAccountChange("gs", e.target.value)
                    }
                  >
                    <option value="">-- Select Sheets --</option>
                    {accounts
                      .filter((a) => a.type === "gs")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium text-content-primary">
                    Telegram (Notify)
                  </label>
                  <Select
                    value={formData.step_accounts?.tg || ""}
                    onChange={(e) =>
                      handleStepAccountChange("tg", e.target.value)
                    }
                  >
                    <option value="">-- Select TG --</option>
                    {accounts
                      .filter((a) => a.type === "tg")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </Select>
                </div>
              </div>
            </div>
          </CardContent>

          <CardFooter className="p-6 border-t border-border-subtle flex justify-end space-x-3">
            <Button variant="ghost" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">
              {pipeline ? "Update Pipeline" : "Create Pipeline"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

export default PipelineForm;
