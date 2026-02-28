import { ChatHistoryEntry } from '../api/client';
import './HistoryTable.css';

interface HistoryTableProps {
  entries: ChatHistoryEntry[];
}

function HistoryTable({ entries }: HistoryTableProps) {
  return (
    <div className="history-table-container">
      <table className="history-table">
        <thead>
          <tr>
            <th>Date & Time</th>
            <th>Question</th>
            <th>Answer</th>
            <th>Model</th>
            <th>Response Time</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td className="date-cell">
                {new Date(entry.created_at).toLocaleString()}
              </td>
              <td className="question-cell">
                <div className="text-preview">{entry.question}</div>
              </td>
              <td className="answer-cell">
                <div className="text-preview">{entry.answer}</div>
              </td>
              <td className="model-cell">
                {entry.model_used || 'N/A'}
              </td>
              <td className="time-cell">
                {entry.response_time_ms ? `${entry.response_time_ms}ms` : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default HistoryTable;
