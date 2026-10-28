import React, { useEffect, useState } from "react";
import { Outlet, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { forgetWorkspaceId, rememberWorkspaceId } from "../context/currentWorkspace";
import { ErrorState, LoadingRegion, SkeletonCard } from "./Feedback";

/** What the server said about the review in the URL. "unverified" means the server couldn't be asked. */
type GuardState = "checking" | "found" | "missing" | "unverified";

export const WorkspaceNotFound: React.FC<{ workspaceId: string; onGoToReviews: () => void }> = ({
  workspaceId,
  onGoToReviews,
}) => (
  <ErrorState
    error={
      new ApiError(
        404,
        "WORKSPACE_NOT_FOUND",
        `There is no review “${workspaceId}” on this server. Reviews can disappear when the service restarts. Open your reviews to pick another or start a new one.`,
      )
    }
    title="This review doesn't exist"
    actionLabel="Go to your reviews"
    onAction={onGoToReviews}
  />
);

/**
 * Wraps every /reviews/:id/... page. Looks the review up once, so a link to a review that is gone
 * shows one clear message instead of a 404 on each section of the page.
 */
export const WorkspaceGuard: React.FC = () => {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<GuardState>("checking");

  useEffect(() => {
    let mounted = true;
    setState("checking");
    api.workspaces
      .list()
      .then((list) => {
        if (!mounted) return;
        if (list.some((w) => w.id === id)) {
          rememberWorkspaceId(id);
          setState("found");
        } else {
          forgetWorkspaceId(id);
          setState("missing");
        }
      })
      .catch(() => {
        // Service down or older backend: let the pages show their own offline states
        if (mounted) setState("unverified");
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  if (state === "checking") {
    return (
      <LoadingRegion label="Opening review">
        <SkeletonCard lines={3} />
      </LoadingRegion>
    );
  }
  if (state === "missing") {
    return <WorkspaceNotFound workspaceId={id} onGoToReviews={() => navigate("/reviews")} />;
  }
  // Keyed by review so page state (saved question, query, selections) never leaks between reviews
  return <Outlet key={id} />;
};
