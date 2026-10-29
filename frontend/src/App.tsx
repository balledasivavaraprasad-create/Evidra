import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthProvider, RequireAuth, useAuth } from "./context/AuthContext";
import { getRememberedWorkspaceId } from "./context/currentWorkspace";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { WorkspaceGuard } from "./components/WorkspaceGuard";
import { ParticleBackground } from "./components/ParticleBackground";
import { LandingPage } from "./features/landing/LandingPage";
import { SignInPage, SignUpPage } from "./features/auth/AuthPages";
import { DashboardPage } from "./features/workspaces/DashboardPage";
import { QueryBuilderPage } from "./features/search/QueryBuilderPage";
import { ReviewQueuePage } from "./features/review-queue/ReviewQueuePage";
import { DuplicatesPage } from "./features/duplicates/DuplicatesPage";
import { HistoryPage } from "./features/history/HistoryPage";
import { MLReviewPage } from "./features/ml-review/MLReviewPage";
import { ReviewRadarDashboard } from "./features/pico-radar/ReviewRadarDashboard";
import { DevilsAdvocateDashboard } from "./features/devils-advocate/DevilsAdvocateDashboard";
import { PrismaFlowPage } from "./features/prisma/PrismaFlowPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/** Old links without a review id: open that section of the last review, or the dashboard. */
const RememberedReviewRedirect: React.FC<{ section: string }> = ({ section }) => {
  const remembered = getRememberedWorkspaceId();
  return (
    <Navigate to={remembered ? `/reviews/${encodeURIComponent(remembered)}/${section}` : "/dashboard"} replace />
  );
};

/** Signed-in people land on their dashboard; everyone else sees the landing page. */
const Home: React.FC = () => {
  const { status } = useAuth();
  return status === "signed-in" ? <Navigate to="/dashboard" replace /> : <LandingPage />;
};

const protectedRoute = (element: React.ReactNode) => <RequireAuth>{element}</RequireAuth>;

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <div className="min-h-screen flex flex-col bg-[var(--bg-base)] text-[var(--text-primary)] transition-colors duration-300">
              <ParticleBackground />
              <Header />
              <main id="main-content" className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-10">
                <ErrorBoundary>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/signin" element={<SignInPage />} />
                    <Route path="/signup" element={<SignUpPage />} />
                    <Route path="/dashboard" element={protectedRoute(<DashboardPage />)} />
                    <Route path="/reviews" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/reviews/:id" element={protectedRoute(<WorkspaceGuard />)}>
                      <Route index element={<Navigate to="setup" replace />} />
                      <Route path="search" element={<QueryBuilderPage />} />
                      <Route path="setup" element={<QueryBuilderPage />} />
                      <Route path="records" element={<ReviewQueuePage />} />
                      <Route path="ml-ranking" element={<MLReviewPage />} />
                      <Route path="duplicates" element={<DuplicatesPage />} />
                      <Route path="history" element={<HistoryPage />} />
                      <Route path="radar" element={<ReviewRadarDashboard />} />
                      <Route path="devils-advocate" element={<DevilsAdvocateDashboard />} />
                      <Route path="prisma" element={<PrismaFlowPage />} />
                      <Route path="search-evolution" element={<HistoryPage initialTab="search_evolution" />} />
                    </Route>
                    <Route path="/radar" element={protectedRoute(<RememberedReviewRedirect section="radar" />)} />
                    <Route
                      path="/devils-advocate"
                      element={protectedRoute(<RememberedReviewRedirect section="devils-advocate" />)}
                    />
                    <Route path="/prisma" element={protectedRoute(<RememberedReviewRedirect section="prisma" />)} />
                    <Route path="/review-queue" element={protectedRoute(<RememberedReviewRedirect section="records" />)} />
                    <Route path="/ml-ranking" element={protectedRoute(<RememberedReviewRedirect section="ml-ranking" />)} />
                    <Route path="/duplicates" element={protectedRoute(<RememberedReviewRedirect section="duplicates" />)} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </ErrorBoundary>
              </main>
              <Footer />
            </div>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>  );
};
