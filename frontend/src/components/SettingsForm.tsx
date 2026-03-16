import { useState } from 'react';
import { Settings, SettingsUpdate } from '../api/client';
import './SettingsForm.css';

interface SettingsFormProps {
  settings: Settings;
  onSave: (settings: SettingsUpdate) => void;
  saving: boolean;
}

function SettingsForm({ settings, onSave, saving }: SettingsFormProps) {
  const [formData, setFormData] = useState<SettingsUpdate>({
    llm_provider: settings.llm_provider,
    llm_model: settings.llm_model,
    llm_temperature: settings.llm_temperature,
    retriever_k: settings.retriever_k,
    pdf_language: settings.pdf_language,
    pdf_strategy: settings.pdf_strategy,
    chunk_max_characters: settings.chunk_max_characters,
    chunk_new_after_n_chars: settings.chunk_new_after_n_chars,
    chunk_overlap: settings.chunk_overlap,
    rag_prompt_template: settings.rag_prompt_template,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    const target = e.target as HTMLInputElement;
    const type = target.type;
    
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === 'number' || type === 'range'
          ? parseFloat(value)
          : value,
    }));
  };

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <div className="form-section">
        <h2>LLM Configuration</h2>

        <div className="form-group">
          <label htmlFor="llm_provider">LLM Provider</label>
          <select
            id="llm_provider"
            name="llm_provider"
            value={formData.llm_provider}
            onChange={handleChange}
            required
          >
            <option value="groq">Groq</option>
            <option value="deepseek">DeepSeek</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="llm_model">LLM Model</label>
          <input
            type="text"
            id="llm_model"
            name="llm_model"
            value={formData.llm_model}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="llm_temperature">
            Temperature ({formData.llm_temperature.toFixed(2)})
          </label>
          <input
            type="range"
            id="llm_temperature"
            name="llm_temperature"
            min="0"
            max="1"
            step="0.01"
            value={formData.llm_temperature}
            onChange={handleChange}
          />
          <div className="slider-labels">
            <span>0.0 (Focused)</span>
            <span>1.0 (Creative)</span>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="retriever_k">Documents to Retrieve (K)</label>
          <input
            type="number"
            id="retriever_k"
            name="retriever_k"
            min="1"
            max="20"
            value={formData.retriever_k}
            onChange={handleChange}
            required
          />
        </div>
      </div>

      <div className="form-section">
        <h2>PDF Processing</h2>

        <div className="form-group">
          <label htmlFor="pdf_language">PDF Language Code</label>
          <input
            type="text"
            id="pdf_language"
            name="pdf_language"
            value={formData.pdf_language}
            onChange={handleChange}
            placeholder="e.g., hun, eng"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="pdf_strategy">PDF Processing Strategy</label>
          <select
            id="pdf_strategy"
            name="pdf_strategy"
            value={formData.pdf_strategy}
            onChange={handleChange}
            required
          >
            <option value="auto">Auto</option>
            <option value="fast">Fast</option>
            <option value="hi_res">High Resolution</option>
            <option value="ocr_only">OCR Only</option>
          </select>
        </div>
      </div>

      <div className="form-section">
        <h2>Chunking Configuration</h2>

        <div className="form-group">
          <label htmlFor="chunk_max_characters">Max Characters per Chunk</label>
          <input
            type="number"
            id="chunk_max_characters"
            name="chunk_max_characters"
            min="100"
            max="5000"
            value={formData.chunk_max_characters}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="chunk_new_after_n_chars">Preferred Chunk Size</label>
          <input
            type="number"
            id="chunk_new_after_n_chars"
            name="chunk_new_after_n_chars"
            min="100"
            max="5000"
            value={formData.chunk_new_after_n_chars}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="chunk_overlap">Chunk Overlap</label>
          <input
            type="number"
            id="chunk_overlap"
            name="chunk_overlap"
            min="0"
            max="1000"
            value={formData.chunk_overlap}
            onChange={handleChange}
            required
          />
        </div>
      </div>

      <div className="form-section">
        <h2>RAG Prompt Template</h2>

        <div className="form-group">
          <label htmlFor="rag_prompt_template">System Prompt</label>
          <textarea
            id="rag_prompt_template"
            name="rag_prompt_template"
            value={formData.rag_prompt_template}
            onChange={handleChange}
            rows={12}
            required
          />
          <small>Use {'{context}'} and {'{question}'} as placeholders</small>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  );
}

export default SettingsForm;
