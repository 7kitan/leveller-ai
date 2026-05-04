"use client";

import { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useAlert } from "@/context/AlertContext";
import Modal from "@/components/shared/Modal";
import api from "@/lib/api";
import styles from "./prompts.module.css";

interface PromptTemplate {
  id: number;
  category: string;
  name: string;
  prompt_text: string;
  parameters: string[];
  llm_config: {
    temperature: number;
    max_tokens: number;
  };
  is_active: boolean;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}

interface PromptMetadata {
  category: string;
  name: string;
  description: string;
  parameters: string[];
  parameter_descriptions: Record<string, string>;
  example_usage: string | null;
}

interface CategoryOption {
  label: string;
  value: string;
}

interface GroupedPrompts {
  [key: string]: PromptTemplate[];
}

export default function PromptsManagementPage() {
  const { t } = useLanguage();
  const { showSuccess, showError, confirm } = useAlert();
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [groupedPrompts, setGroupedPrompts] = useState<GroupedPrompts>({});
  const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
  const [metadata, setMetadata] = useState<PromptMetadata[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<PromptTemplate | null>(null);

  // Copy parameter to clipboard
  const copyParameter = (param: string) => {
    const textToCopy = `{{${param}}}`;
    navigator.clipboard.writeText(textToCopy).then(() => {
      showSuccess(`Copied: ${textToCopy}`);
    }).catch(() => {
      showError("Failed to copy to clipboard");
    });
  };

  // Fetch prompts
  const fetchPrompts = async () => {
    try {
      setLoading(true);
      const params: any = {};
      
      // Filter by category if a specific prompt is selected
      if (selectedCategory !== "all") {
        params.category = selectedCategory;
      }

      const response = await api.get("admin/prompts", { params });
      const data = response.data;
      setPrompts(data);

      // Group prompts by category
      const grouped: GroupedPrompts = {};
      data.forEach((prompt: PromptTemplate) => {
        if (!grouped[prompt.category]) {
          grouped[prompt.category] = [];
        }
        grouped[prompt.category].push(prompt);
      });

      // Sort each group: active first, then by created_at desc
      Object.keys(grouped).forEach((category) => {
        grouped[category].sort((a, b) => {
          if (a.is_active && !b.is_active) return -1;
          if (!a.is_active && b.is_active) return 1;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      });

      setGroupedPrompts(grouped);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch metadata and build category options
  const fetchCategories = async () => {
    try {
      const response = await api.get("admin/prompts/categories");
      const metadataList = response.data;
      
      // Build category options with name as label, category as value
      const options: CategoryOption[] = metadataList.map((m: PromptMetadata) => ({
        label: m.name,
        value: m.category
      }));
      
      setCategoryOptions(options);
      setMetadata(metadataList);
    } catch (err) {
      console.error("Failed to fetch categories:", err);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchPrompts();
  }, [selectedCategory]);

  // Activate prompt
  const handleActivate = async (promptId: number) => {
    try {
      await api.post(`admin/prompts/${promptId}/activate`);
      await fetchPrompts();
      showSuccess("Prompt activated successfully");
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message);
    }
  };

  // Delete prompt
  const handleDelete = async (promptId: number, promptName: string) => {
    const confirmed = await confirm({
      title: "Delete Prompt",
      message: `Are you sure you want to delete "${promptName}"?`,
      confirmText: "Delete",
      cancelText: "Cancel",
      variant: "danger"
    });
    
    if (!confirmed) return;

    try {
      await api.delete(`admin/prompts/${promptId}`);
      await fetchPrompts();
      showSuccess("Prompt deleted successfully");
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message);
    }
  };

  // Reload all prompts to Redis
  const handleReloadCache = async () => {
    try {
      const response = await api.post("admin/prompts/reload");
      showSuccess(response.data.message);
    } catch (err: any) {
      showError(err.response?.data?.detail || err.message);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading prompts...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>LLM Prompt Management</h1>
        <div className={styles.actions}>
          <button
            className={styles.btnReload}
            onClick={handleReloadCache}
            title="Reload all active prompts to Redis cache"
          >
            🔄 Reload Cache
          </button>
          <button
            className={styles.btnPrimary}
            onClick={() => setShowCreateModal(true)}
          >
            + Create New Prompt
          </button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {/* Category Filter */}
      <div className={styles.filters}>
        <label>Filter by Prompt:</label>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className={styles.select}
        >
          <option value="all">All Prompts</option>
          {categoryOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Grouped Prompts List */}
      <div className={styles.promptGroups}>
        {Object.keys(groupedPrompts).length === 0 ? (
          <div className={styles.empty}>
            No prompts found. Create your first prompt to get started.
          </div>
        ) : (
          Object.entries(groupedPrompts).map(([category, promptList]) => {
            // Find metadata for this category to get friendly name
            const meta = metadata.find(m => m.category === category);
            const displayName = meta?.name || category;
            
            return (
            <div key={category} className={styles.promptGroup}>
              <div className={styles.groupHeader}>
                <h3>📁 {displayName}</h3>
                <span className={styles.groupCount}>
                  {promptList.length} version{promptList.length > 1 ? "s" : ""}
                </span>
              </div>

              <div className={styles.promptList}>
                {promptList.map((prompt) => (
                  <div
                    key={prompt.id}
                    className={`${styles.promptCard} ${
                      prompt.is_active ? styles.active : styles.inactive
                    }`}
                  >
                    <div className={styles.promptHeader}>
                      <div className={styles.promptTitle}>
                        <span className={styles.promptName}>{prompt.name}</span>
                        {prompt.is_active && (
                          <span className={styles.badge}>ACTIVE</span>
                        )}
                      </div>
                      <div className={styles.promptActions}>
                        <button
                          className={styles.btnEdit}
                          onClick={() => setEditingPrompt(prompt)}
                          title="Edit prompt"
                        >
                          ✏️ Edit
                        </button>
                        {!prompt.is_active && (
                          <button
                            className={styles.btnActivate}
                            onClick={() => handleActivate(prompt.id)}
                            title="Set as active"
                          >
                            ✅ Activate
                          </button>
                        )}
                        <button
                          className={styles.btnDelete}
                          onClick={() => handleDelete(prompt.id, prompt.name)}
                          title="Delete prompt"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    <div className={styles.promptMeta}>
                      <span className={styles.category}>{prompt.category}</span>
                      <span className={styles.params}>
                        Parameters: {prompt.parameters.join(", ")}
                      </span>
                      <span className={styles.config}>
                        Temp: {prompt.llm_config.temperature} | Max tokens:{" "}
                        {prompt.llm_config.max_tokens}
                      </span>
                    </div>

                    {/* Show parameter descriptions from metadata */}
                    {metadata.find(m => m.category === prompt.category) && (
                      <div className={styles.parameterInfo}>
                        <details>
                          <summary>📋 Parameter Details</summary>
                          <div className={styles.parameterList}>
                            {metadata.find(m => m.category === prompt.category)?.parameters.map(param => (
                              <div key={param} className={styles.parameterItem}>
                                <code 
                                  className={styles.clickableParam}
                                  onClick={() => copyParameter(param)}
                                  title="Click to copy"
                                >{`{{${param}}}`}</code>
                                <span>{metadata.find(m => m.category === prompt.category)?.parameter_descriptions[param]}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}

                    {prompt.admin_notes && (
                      <div className={styles.adminNotes}>
                        <strong>Notes:</strong> {prompt.admin_notes}
                      </div>
                    )}

                    <div className={styles.promptPreview}>
                      <details>
                        <summary>View Prompt Text</summary>
                        <pre className={styles.promptText}>
                          {prompt.prompt_text}
                        </pre>
                      </details>
                    </div>

                    <div className={styles.promptFooter}>
                      <span className={styles.timestamp}>
                        Updated: {new Date(prompt.updated_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            );
          })
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingPrompt) && (
        <PromptFormModal
          prompt={editingPrompt}
          metadata={metadata}
          onClose={() => {
            setShowCreateModal(false);
            setEditingPrompt(null);
          }}
          onSuccess={() => {
            setShowCreateModal(false);
            setEditingPrompt(null);
            fetchPrompts();
          }}
        />
      )}
    </div>
  );
}

// Prompt Form Modal Component
interface PromptFormModalProps {
  prompt: PromptTemplate | null;
  metadata: PromptMetadata[];
  onClose: () => void;
  onSuccess: () => void;
}

// Prompt Form Modal Component
interface PromptFormModalProps {
  prompt: PromptTemplate | null;
  metadata: PromptMetadata[];
  onClose: () => void;
  onSuccess: () => void;
}

function PromptFormModal({ prompt, metadata, onClose, onSuccess }: PromptFormModalProps) {
  const { t } = useLanguage();
  const { showSuccess, showError } = useAlert();
  const isEdit = !!prompt;
  const [formData, setFormData] = useState({
    name: prompt?.name || "",
    category: prompt?.category || "",
    prompt_text: prompt?.prompt_text || "",
    temperature: prompt?.llm_config.temperature ?? 0.7,
    max_tokens: prompt?.llm_config.max_tokens ?? 2000,
    is_active: prompt?.is_active ?? false,
    admin_notes: prompt?.admin_notes || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Copy parameter to clipboard
  const copyParameter = (param: string) => {
    const textToCopy = `{{${param}}}`;
    navigator.clipboard.writeText(textToCopy).then(() => {
      showSuccess(`Copied: ${textToCopy}`);
    }).catch(() => {
      showError("Failed to copy to clipboard");
    });
  };

  // Auto-extract parameters from prompt text
  const extractParameters = (text: string): string[] => {
    const matches = text.match(/\{\{(\w+)\}\}/g);
    if (!matches) return [];
    
    const params = matches.map(m => m.replace(/\{\{|\}\}/g, ''));
    // Return unique parameters
    return [...new Set(params)];
  };

  // Get current parameters from prompt text
  const currentParameters = extractParameters(formData.prompt_text);

  // Get metadata for selected key
  const selectedMetadata = metadata.find(m => m.category === formData.category);

  // Handle category change
  const handleCategoryChange = (newCategory: string) => {
    setFormData({ ...formData, category: newCategory });
  };

  // Get unique categories from metadata
  const uniqueCategories = Array.from(new Set(metadata.map(m => m.category)));
  
  // Get metadata for selected category (pick first one if multiple prompts share same category)
  const categoryMetadata = metadata.find(m => m.category === formData.category);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      // Auto-extract parameters from prompt text
      const parameters = extractParameters(formData.prompt_text);

      if (parameters.length === 0) {
        throw new Error("Prompt must contain at least one parameter (e.g., {{param_name}})");
      }

      const payload = {
        name: formData.name,
        category: formData.category,
        prompt_text: formData.prompt_text,
        parameters,
        llm_config: {
          temperature: formData.temperature,
          max_tokens: formData.max_tokens,
        },
        is_active: formData.is_active,
        admin_notes: formData.admin_notes || null,
      };

      if (isEdit) {
        await api.put(`admin/prompts/${prompt.id}`, payload);
      } else {
        await api.post("admin/prompts", payload);
      }

      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={isEdit ? t("admin_prompts_edit_title") : t("admin_prompts_create_title")}
      maxWidth="50rem"
    >
      <form onSubmit={handleSubmit} className={styles.form}>
        {error && <div className={styles.error}>{error}</div>}

          <div className={styles.formGroup}>
            <label>
              Name <span className={styles.required}>*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="CV Parsing v2 - Detailed"
              required
              className={styles.input}
            />
            <small>Human-readable name for this prompt version</small>
          </div>

          <div className={styles.formGroup}>
            <label>
              Category <span className={styles.required}>*</span>
            </label>
            <select
              value={formData.category}
              onChange={(e) => handleCategoryChange(e.target.value)}
              required
              className={styles.select}
            >
              <option value="">-- Select Category --</option>
              {uniqueCategories.map((category) => {
                const meta = metadata.find(m => m.category === category);
                return (
                  <option key={category} value={category}>
                    {meta?.name || category} ({category})
                  </option>
                );
              })}
            </select>
            <small>Select category to see expected parameters</small>
            
            {/* Show expected parameters for selected category */}
            {categoryMetadata && (
              <div className={styles.metadataInfo}>
                <div className={styles.description}>
                  <strong>📝 Description:</strong> {categoryMetadata.description}
                </div>
                  <div className={styles.expectedParams}>
                    <strong>📋 Expected Parameters:</strong>
                    <div className={styles.parameterList}>
                      {categoryMetadata.parameters.map((param) => (
                        <div key={param} className={styles.parameterItem}>
                          <code 
                            className={styles.clickableParam}
                            onClick={() => copyParameter(param)}
                            title="Click to copy"
                          >{`{{${param}}}`}</code>
                          <span>{categoryMetadata.parameter_descriptions[param]}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                {categoryMetadata.example_usage && (
                  <div className={styles.exampleUsage}>
                    <strong>💡 Usage:</strong> {categoryMetadata.example_usage}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className={styles.formGroup}>
            <label>
              Prompt Text <span className={styles.required}>*</span>
            </label>
            <textarea
              value={formData.prompt_text}
              onChange={(e) =>
                setFormData({ ...formData, prompt_text: e.target.value })
              }
              placeholder="Use {{parameter}} for placeholders"
              required
              rows={10}
              className={styles.textarea}
            />
            <small>Use {`{{parameter_name}}`} for dynamic values</small>
            
            {/* Auto-detected parameters */}
            {currentParameters.length > 0 && (
              <div className={styles.detectedParams}>
                <strong>✓ Detected parameters:</strong>{" "}
                {currentParameters.map((p, i) => (
                  <span 
                    key={i} 
                    className={styles.paramTag}
                    onClick={() => copyParameter(p)}
                    title="Click to copy"
                  >
                    {`{{${p}}}`}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={formData.temperature}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    temperature: parseFloat(e.target.value),
                  })
                }
                className={styles.input}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Max Tokens</label>
              <input
                type="number"
                step="100"
                min="100"
                max="10000"
                value={formData.max_tokens}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_tokens: parseInt(e.target.value),
                  })
                }
                className={styles.input}
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.checkbox}>
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) =>
                  setFormData({ ...formData, is_active: e.target.checked })
                }
              />
              <span>Set as active (will deactivate other prompts with same key)</span>
            </label>
          </div>

          <div className={styles.formGroup}>
            <label>Admin Notes</label>
            <textarea
              value={formData.admin_notes}
              onChange={(e) =>
                setFormData({ ...formData, admin_notes: e.target.value })
              }
              placeholder="Quality evaluation, test results, etc."
              rows={3}
              className={styles.textarea}
            />
          </div>

          <div className={styles.formActions}>
            <button
              type="button"
              onClick={onClose}
              className={styles.btnSecondary}
              disabled={saving}
            >
              {t("admin_prompts_cancel")}
            </button>
            <button
              type="submit"
              className={styles.btnPrimary}
              disabled={saving}
            >
              {saving ? t("admin_prompts_saving") : isEdit ? t("admin_prompts_update_btn") : t("admin_prompts_create_btn")}
            </button>
          </div>
        </form>
      </Modal>
  );
}
