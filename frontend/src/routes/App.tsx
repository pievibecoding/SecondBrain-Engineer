import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ProtectedRoute } from "./_protected";
import { AdminLayout } from "./admin/AdminLayout";
import { ChatPage } from "./chat";
import { SignInPage } from "./sign-in";
import { WikiIndexPage } from "./wiki";
import { WikiEntityPage } from "./wiki/[name]";
import { GraphPage } from "./graph";
import { AdminNasQueuePage } from "./admin/nas-queue";
import { AdminDocumentsPage } from "./admin/documents";
import { AdminFoldersPage } from "./admin/folders";
import { AdminDiagnosticsPage } from "./admin/diagnostics";
import { AdminAdaptiveChunkingPage } from "./admin/adaptive-chunking";
import { AdminPdfParserComparisonPage } from "./admin/pdf-parser-comparison";

export function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/wiki" element={<WikiIndexPage />} />
          <Route path="/wiki/:name" element={<WikiEntityPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<Navigate to="/admin/nas-queue" replace />} />
            <Route path="/admin/nas-queue" element={<AdminNasQueuePage />} />
            <Route path="/admin/documents" element={<AdminDocumentsPage />} />
            <Route path="/admin/folders" element={<AdminFoldersPage />} />
            <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
            <Route path="/admin/evaluations/adaptive-chunking" element={<AdminAdaptiveChunkingPage />} />
            <Route path="/admin/evaluations/pdf-parser-comparison" element={<AdminPdfParserComparisonPage />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}
