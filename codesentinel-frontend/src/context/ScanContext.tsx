import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import {
  AnalyzePRRequest,
  AnalyzePRResponse,
  ScoreFileResponse,
  SystemHealth
} from '../types';
import { CodeSentinelApi, formatApiError } from '../services/api';

interface ScanContextType {
  // File scan state
  currentScanResult: ScoreFileResponse | null;
  currentCodeSnippet: string;
  currentLanguage: string;
  isScanning: boolean;
  scanError: string | null;
  runFileScan: (code: string, language?: string) => Promise<ScoreFileResponse>;
  clearCurrentScan: () => void;

  // PR scan state
  currentPRResult: AnalyzePRResponse | null;
  isPRScanning: boolean;
  prError: string | null;
  runPRScan: (params: AnalyzePRRequest) => Promise<AnalyzePRResponse>;
  clearPRScan: () => void;

  // Backend health & connectivity
  health: SystemHealth;
  refreshHealth: () => Promise<void>;
}

const ScanContext = createContext<ScanContextType | undefined>(undefined);

export const ScanProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentScanResult, setCurrentScanResult] = useState<ScoreFileResponse | null>(() => {
    const cached = localStorage.getItem('codesentinel_last_scan');
    if (cached) {
      try { return JSON.parse(cached); } catch { return null; }
    }
    return null;
  });

  const [currentCodeSnippet, setCurrentCodeSnippet] = useState<string>(() => {
    return localStorage.getItem('codesentinel_last_code') || '';
  });

  const [currentLanguage, setCurrentLanguage] = useState<string>(() => {
    return localStorage.getItem('codesentinel_last_lang') || 'auto';
  });

  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  const [currentPRResult, setCurrentPRResult] = useState<AnalyzePRResponse | null>(null);
  const [isPRScanning, setIsPRScanning] = useState(false);
  const [prError, setPrError] = useState<string | null>(null);

  const [health, setHealth] = useState<SystemHealth>({
    status: 'checking',
  });

  const refreshHealth = useCallback(async () => {
    const res = await CodeSentinelApi.checkHealth();
    setHealth(res);
  }, []);

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 15000); // Check every 15s
    return () => clearInterval(interval);
  }, [refreshHealth]);

  const runFileScan = async (code: string, language = 'auto'): Promise<ScoreFileResponse> => {
    setIsScanning(true);
    setScanError(null);
    setCurrentCodeSnippet(code);
    setCurrentLanguage(language);
    localStorage.setItem('codesentinel_last_code', code);
    localStorage.setItem('codesentinel_last_lang', language);

    try {
      const response = await CodeSentinelApi.scoreFile({ code_snippet: code, language });
      setCurrentScanResult(response);
      localStorage.setItem('codesentinel_last_scan', JSON.stringify(response));
      return response;
    } catch (err) {
      const errorMsg = formatApiError(err);
      setScanError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setIsScanning(false);
    }
  };

  const clearCurrentScan = () => {
    setCurrentScanResult(null);
    setCurrentCodeSnippet('');
    setScanError(null);
    localStorage.removeItem('codesentinel_last_scan');
    localStorage.removeItem('codesentinel_last_code');
  };

  const runPRScan = async (params: AnalyzePRRequest): Promise<AnalyzePRResponse> => {
    setIsPRScanning(true);
    setPrError(null);

    try {
      const response = await CodeSentinelApi.analyzePR(params);
      setCurrentPRResult(response);
      return response;
    } catch (err) {
      const errorMsg = formatApiError(err);
      setPrError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setIsPRScanning(false);
    }
  };

  const clearPRScan = () => {
    setCurrentPRResult(null);
    setPrError(null);
  };

  return (
    <ScanContext.Provider
      value={{
        currentScanResult,
        currentCodeSnippet,
        currentLanguage,
        isScanning,
        scanError,
        runFileScan,
        clearCurrentScan,
        currentPRResult,
        isPRScanning,
        prError,
        runPRScan,
        clearPRScan,
        health,
        refreshHealth,
      }}
    >
      {children}
    </ScanContext.Provider>
  );
};

export const useScan = (): ScanContextType => {
  const context = useContext(ScanContext);
  if (!context) {
    throw new Error('useScan must be used within a ScanProvider');
  }
  return context;
};
