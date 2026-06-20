import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export function AdminLayout() {
  const { isAdmin } = useAuth();
  if (!isAdmin) {
    return <Navigate to="/chat" replace />;
  }
  return (
    <div className="admin-layout">
      <aside className="admin-nav card">
        <NavLink to="/admin/nas-queue">NAS Queue</NavLink>
        <NavLink to="/admin/documents">Documents</NavLink>
        <NavLink to="/admin/folders">Folders</NavLink>
        <NavLink to="/admin/diagnostics">Diagnostics</NavLink>
        <NavLink to="/admin/evaluations/adaptive-chunking">Adaptive Chunking</NavLink>
        <NavLink to="/admin/evaluations/pdf-parser-comparison">PDF Parser</NavLink>
      </aside>
      <div className="admin-content"><Outlet /></div>
    </div>
  );
}
