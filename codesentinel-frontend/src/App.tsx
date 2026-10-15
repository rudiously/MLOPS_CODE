import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ScanProvider } from './context/ScanContext';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { CodeScannerPage } from './pages/CodeScannerPage';
import { VulnerabilityResultsPage } from './pages/VulnerabilityResultsPage';
import { GitHubPRPage } from './pages/GitHubPRPage';
import { ScanHistoryPage } from './pages/ScanHistoryPage';
import { SecurityReportsPage } from './pages/SecurityReportsPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <ScanProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="scanner" element={<CodeScannerPage />} />
            <Route path="results" element={<VulnerabilityResultsPage />} />
            <Route path="pull-request" element={<GitHubPRPage />} />
            <Route path="history" element={<ScanHistoryPage />} />
            <Route path="reports" element={<SecurityReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ScanProvider>
  );
}

export default App;
