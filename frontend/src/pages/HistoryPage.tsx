import { useState, useEffect } from 'react';
import { apiClient, ChatHistoryResponse } from '../api/client';
import HistoryTable from '../components/HistoryTable';
import './HistoryPage.css';

function HistoryPage() {
  const [history, setHistory] = useState<ChatHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  useEffect(() => {
    loadHistory();
  }, [page, search]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getChatHistory(page, 20, search || undefined);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat history');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearch('');
    setPage(1);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  if (loading && !history) {
    return (
      <div className="history-page">
        <div className="loading">Loading chat history...</div>
      </div>
    );
  }

  if (error && !history) {
    return (
      <div className="history-page">
        <div className="error-message">
          <p>Error: {error}</p>
          <button onClick={loadHistory}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="history-header">
        <h1>Chat History</h1>
        <p className="history-description">
          View all question-answer pairs logged by the system. Use this to monitor AI performance and review conversations.
        </p>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search questions or answers..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="search-input"
        />
        <button type="submit">Search</button>
        {search && (
          <button type="button" onClick={handleClearSearch}>
            Clear
          </button>
        )}
      </form>

      {history && (
        <>
          <div className="history-stats">
            <span>Total entries: {history.total}</span>
            <span>Page {history.page} of {history.total_pages}</span>
          </div>

          <HistoryTable entries={history.items} />

          {history.total_pages > 1 && (
            <div className="pagination">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 1 || loading}
              >
                Previous
              </button>
              <span>Page {page} of {history.total_pages}</span>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= history.total_pages || loading}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {history && history.items.length === 0 && (
        <div className="empty-state">
          {search ? (
            <p>No results found for "{search}"</p>
          ) : (
            <p>No chat history yet. Start a conversation to see entries here.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default HistoryPage;
