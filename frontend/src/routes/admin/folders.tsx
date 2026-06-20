import { FormEvent, useState } from "react";
import { useFolders } from "../../hooks/useFolders";

export function AdminFoldersPage() {
  const { folders, loading, error, create, remove, scan, scanResult, scanningFolderId } = useFolders();
  const [path, setPath] = useState("/projects");
  const [folderType, setFolderType] = useState<"auto" | "manual">("manual");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void create(path, folderType);
  };
  const summary = scanResult
    ? `Scanned ${scanResult.scanned_count} file(s): ${scanResult.new_count} new, ${scanResult.updated_count} updated, ${scanResult.deleted_count} deleted, ${scanResult.queued_count} queued/reviewed, ${scanResult.ingested_count} ingested, ${scanResult.error_count} error(s).`
    : null;
  return (
    <section className="card">
      <h1>NAS Folders</h1>
      <form className="inline-form" onSubmit={submit}>
        <input value={path} onChange={(event) => setPath(event.target.value)} placeholder="/projects" />
        <select value={folderType} onChange={(event) => setFolderType(event.target.value as "auto" | "manual")}>
          <option value="manual">Manual review</option>
          <option value="auto">Auto sync</option>
        </select>
        <button type="submit">Add folder</button>
      </form>
      {scanResult ? (
        <div className="status-banner">
          <strong>Last scan:</strong> {summary}
          {scanResult.errors.length ? <div className="status-banner-errors">{scanResult.errors.join(" | ")}</div> : null}
        </div>
      ) : null}
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error.message}</p> : null}
      <table>
        <thead><tr><th>Path</th><th>Type</th><th>Active</th><th>Last scanned</th><th>Actions</th></tr></thead>
        <tbody>
          {folders.map((folder) => (
            <tr key={folder.id}>
              <td>{folder.path}</td>
              <td>{folder.folder_type}</td>
              <td>{folder.is_active ? "Yes" : "No"}</td>
              <td>{folder.last_scanned ? new Date(folder.last_scanned).toLocaleString() : "-"}</td>
              <td className="actions">
                <button
                  className="secondary"
                  type="button"
                  disabled={scanningFolderId === folder.id}
                  onClick={() => void scan(folder.id)}
                >
                  {scanningFolderId === folder.id ? "Scanning..." : "Scan now"}
                </button>
                <button className="secondary" type="button" onClick={() => void remove(folder.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
