import { useCallback, useEffect, useRef, useState } from "react";
import { api, type JobResponse } from "../../api/client";
import { newestJob } from "../search/setupData";
import { isActiveJob } from "./processing";

const POLL_MS = 2000;

/**
 * The workspace's newest processing (screen) job: loaded on mount, polled while it is queued or
 * running, and reported once when it finishes. `track` follows a job that was just queued.
 */
export function useProcessingJob(workspaceId: string, onFinished?: (job: JobResponse) => void) {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const finishedRef = useRef(onFinished);
  finishedRef.current = onFinished;

  const refresh = useCallback(async () => {
    try {
      const jobs = await api.jobs.listForWorkspace(workspaceId, "screen", 5);
      setJob(newestJob(jobs));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't check on processing");
    } finally {
      setLoaded(true);
    }
  }, [workspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const activeId = isActiveJob(job) ? job?.id : undefined;
  useEffect(() => {
    if (!activeId) return;
    let stopped = false;
    const timer = window.setInterval(async () => {
      try {
        const updated = await api.jobs.get(activeId);
        if (stopped) return;
        setJob(updated);
        if (!isActiveJob(updated)) finishedRef.current?.(updated);
      } catch {
        /* a missed poll is not an error: try again on the next tick */
      }
    }, POLL_MS);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [activeId]);

  return { job, error, loaded, track: setJob, refresh };
}
