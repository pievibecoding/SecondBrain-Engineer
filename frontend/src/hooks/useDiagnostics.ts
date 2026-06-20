import { useState } from "react";
import * as adminApi from "../api/admin";
import { logApiError } from "../api/client";
import type { DiagnosticRequest, DiagnosticResponse } from "../types";

export function useDiagnostics() {
  const [result, setResult] = useState<DiagnosticResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const run = async (payload: DiagnosticRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await adminApi.runDiagnostic(payload);
      setResult(response);
      return response;
    } catch (nextError) {
      logApiError("runDiagnostic failed", nextError, { query: payload.query });
      setError(nextError as Error);
      throw nextError;
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, run };
}
