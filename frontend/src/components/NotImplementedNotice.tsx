import React from "react";
import { Clock, Info } from "lucide-react";

interface Props {
  featureName: string;
  taskOwner: string;
  targetTask: string;
  description: string;
}

export const NotImplementedNotice: React.FC<Props> = ({
  featureName,
  taskOwner,
  targetTask,
  description,
}) => {
  return (
    <div className="glass-panel p-6 border-indigo-500/20 bg-indigo-950/20 rounded-xl my-4">
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
          <Clock className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-white text-sm">{featureName} — Under Construction</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
              Assigned: {targetTask} ({taskOwner})
            </span>
          </div>
          <p className="text-slate-300 text-xs mb-3">{description}</p>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
            <Info className="w-3.5 h-3.5 text-cyan-400" />
            Backend returns contract 501 until {targetTask} merges. Showing interactive mock preview.
          </div>
        </div>
      </div>
    </div>
  );
};
