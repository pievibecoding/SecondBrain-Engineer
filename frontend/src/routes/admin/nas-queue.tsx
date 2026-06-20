import { useState } from "react";
import { useNasQueue } from "../../hooks/useNasQueue";

export function AdminNasQueuePage() {
  const { files, loading, error, approve, reject, bulkApprove } = useNasQueue();
  const [selected, setSelected] = useState<string[]>([]);
  const toggle = (id: string) => setSelected((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  return (
    <section className="card">
      <div className="section-header">
        <h1>NAS Review Queue</h1>
        <button type="button" disabled={!selected.length} onClick={() => void bulkApprove(selected)}>Bulk approve</button>
      </div>
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error.message}</p> : null}
      <table>
        <thead><tr><th>Select</th><th>Path</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td><input aria-label={`Select ${file.nas_path}`} type="checkbox" checked={selected.includes(file.id)} onChange={() => toggle(file.id)} /></td>
              <td>{file.nas_path}</td>
              <td>{file.status}</td>
              <td>{new Date(file.created_at).toLocaleString()}</td>
              <td className="actions">
                <button type="button" onClick={() => void approve(file.id)}>Approve</button>
                <button className="secondary" type="button" onClick={() => {
                  const reason = window.prompt("Reject reason");
                  if (reason) void reject(file.id, reason);
                }}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
