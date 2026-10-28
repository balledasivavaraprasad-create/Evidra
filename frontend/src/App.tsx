import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthGate } from "./context/AuthContext";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { WorkspaceGuard } from "./components/WorkspaceGuard";
import { ParticleBackground } from "./components/ParticleBackground";
import { LandingPage } from "./features/landing/LandingPage";
import { WorkspacesPage } from "./features/workspaces/WorkspacesPage";
import { QueryBuilderPage } from "./features/search/QueryBuilderPage";
import { ReviewQueuePage } from "./features/review-queue/ReviewQueuePage";
import { DuplicatesPage } from "./features/duplicates/DuplicatesPage";
import { HistoryPage } from "./features/history/HistoryPage";
import { MLReviewPage } from "./features/ml-review/MLReviewPage";
import { ReviewRadarDashboard } from "./features/pico-radar/ReviewRadarDashboard";
import { DevilsAdvocateDashboard } from "./features/devils-advocate/DevilsAdvocateDashboard";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthGate>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="min-h-screen flex flex-col bg-[var(--bg-base)] text-[var(--text-primary)] transition-colors duration-300">
            <ParticleBackground />
            <Header />
          <main id="main-content" className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-10">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/reviews" element={<WorkspacesPage />} />
                <Route path="/reviews/:id" element={<WorkspaceGuard />}>
                  <Route path="search" element={<QueryBuilderPage />} />
                  <Route path="setup" element={<QueryBuilderPage />} />
                  <Route path="records" element={<ReviewQueuePage />} />
                  <Route path="ml-ranking" element={<MLReviewPage />} />
                  <Route path="duplicates" element={<DuplicatesPage />} />
                  <Route path="history" element={<HistoryPage />} />
                  <Route path="radar" element={<ReviewRadarDashboard />} />
                  <Route path="devils-advocate" element={<DevilsAdvocateDashboard />} />
                  <Route path="search-evolution" element={<HistoryPage initialTab="search_evolution" />} />
                </Route>
                <Route path="/radar" element={<ReviewRadarDashboard />} />
                <Route path="/devils-advocate" element={<DevilsAdvocateDashboard />} />
                <Route path="/review-queue" element={<ReviewQueuePage />} />
                <Route path="/ml-ranking" element={<MLReviewPage />} />
                <Route path="/duplicates" element={<DuplicatesPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
      </AuthGate>
  </ThemeProvider>
  );
};
