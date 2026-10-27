import React, { useState, useRef } from "react";
import { Tag, Sparkles, AlertCircle, Check, Undo2, Save, X } from "lucide-react";
import type { PicoSpan, PicoLabel } from "../../api/client";
import { utf16ToCodePoint, codePointToUtf16, sliceByCodePoints, validateSpanQuote } from "./offsets";

interface PicoViewerProps {
  abstractText: string | null;
  contentHash: string;
  initialSpans: PicoSpan[];
  comparatorAbsent?: boolean;
  onSaveSpans: (spans: PicoSpan[]) => Promise<void>;
  readOnly?: boolean;
}

const LABEL_CONFIG: Record<PicoLabel, { name: string; bg: string; text: string; border: string; highlight: string }> = {
  P: {
    name: "Population",
    bg: "bg-cyan-950/80",
    text: "text-cyan-300",
    border: "border-cyan-700/80",
    highlight: "bg-cyan-500/20 text-cyan-200 border-b-2 border-cyan-400",
  },
  I: {
    name: "Intervention",
    bg: "bg-purple-950/80",
    text: "text-purple-300",
    border: "border-purple-700/80",
    highlight: "bg-purple-500/20 text-purple-200 border-b-2 border-purple-400",
  },
  C: {
    name: "Comparator",
    bg: "bg-amber-950/80",
    text: "text-amber-300",
    border: "border-amber-700/80",
    highlight: "bg-amber-500/20 text-amber-200 border-b-2 border-amber-400",
  },
  O: {
    name: "Outcome",
    bg: "bg-emerald-950/80",
    text: "text-emerald-300",
    border: "border-emerald-700/80",
    highlight: "bg-emerald-500/20 text-emerald-200 border-b-2 border-emerald-400",
  },
};

export const PicoViewer: React.FC<PicoViewerProps> = ({
  abstractText,
  contentHash,
  initialSpans,
  comparatorAbsent = false,
  onSaveSpans,
  readOnly = false,
}) => {
  const [spans, setSpans] = useState<PicoSpan[]>(initialSpans);
  const [draftSelection, setDraftSelection] = useState<{ startCp: number; endCp: number; quote: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const textRef = useRef<HTMLDivElement>(null);

  if (!abstractText) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-xs italic">
        No abstract text available for PICO extraction.
      </div>
    );
  }

  const handleMouseUp = () => {
    if (readOnly) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      return;
    }

    const selectedText = selection.toString().trim();
    // Locate the selected substring in abstract text
    // (For precision, find exact match in abstract)
    const utf16Start = abstractText.indexOf(selectedText);
    if (utf16Start === -1) return;

    const utf16End = utf16Start + selectedText.length;
    const startCp = utf16ToCodePoint(abstractText, utf16Start);
    const endCp = utf16ToCodePoint(abstractText, utf16End);
    const quote = sliceByCodePoints(abstractText, startCp, endCp);

    if (validateSpanQuote(abstractText, startCp, endCp, quote)) {
      setDraftSelection({ startCp, endCp, quote });
    }
  };

  const addSpan = (label: PicoLabel) => {
    if (!draftSelection) return;
    const newSpan: PicoSpan = {
      label,
      start_cp: draftSelection.startCp,
      end_cp: draftSelection.endCp,
      quote: draftSelection.quote,
      provenance: "human_override",
    };
    // Append or replace
    const updated = [...spans.filter((s) => !(s.start_cp === newSpan.start_cp && s.end_cp === newSpan.end_cp && s.label === label)), newSpan];
    setSpans(updated);
    setDraftSelection(null);
    setSaveSuccess(false);
  };

  const removeSpan = (index: number) => {
    const updated = [...spans];
    updated.splice(index, 1);
    setSpans(updated);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSaveSpans(spans);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save PICO annotations";
      setErrorMessage(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // Render highlights inside the text
  // Sort spans by start_cp
  const sortedSpans = [...spans].sort((a, b) => a.start_cp - b.start_cp);

  return (
    <div className="space-y-4">
      {/* PICO Legend & Tag Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-slate-400 font-semibold flex items-center gap-1">
            <Tag className="w-3.5 h-3.5 text-cyan-400" />
            <span>PICO Annotations:</span>
          </span>
          {(["P", "I", "C", "O"] as PicoLabel[]).map((lbl) => {
            const conf = LABEL_CONFIG[lbl];
            const count = spans.filter((s) => s.label === lbl).length;
            return (
              <span
                key={lbl}
                className={`px-2 py-0.5 rounded border text-[11px] flex items-center gap-1 ${conf.bg} ${conf.text} ${conf.border}`}
              >
                <span className="font-bold">{lbl}</span>
                <span>• {conf.name}</span>
                <span className="ml-1 px-1 rounded bg-black/40 text-[10px] font-bold">{count}</span>
              </span>
            );
          })}
          {comparatorAbsent && (
            <span className="px-2 py-0.5 rounded border border-amber-800/60 bg-amber-950/40 text-amber-400 text-[11px] italic">
              Comparator: Absent (Single-Arm)
            </span>
          )}
        </div>

        {!readOnly && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs shadow transition disabled:opacity-50"
            >
              {saveSuccess ? <Check className="w-3.5 h-3.5 text-emerald-200" /> : <Save className="w-3.5 h-3.5" />}
              <span>{isSaving ? "Saving..." : saveSuccess ? "Saved!" : "Save PICO"}</span>
            </button>
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="p-3 rounded-lg bg-red-950/80 border border-red-800 text-red-200 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </span>
          <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Floating Selection Action Pill */}
      {draftSelection && !readOnly && (
        <div className="p-2.5 rounded-xl bg-slate-900 border border-cyan-500/80 shadow-lg shadow-cyan-500/20 flex flex-wrap items-center justify-between gap-3 text-xs font-mono animate-fadeIn">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-300">Selected &quot;{draftSelection.quote.slice(0, 30)}{draftSelection.quote.length > 30 ? "..." : ""}&quot;</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 mr-1 text-[11px]">Tag as:</span>
            {(["P", "I", "C", "O"] as PicoLabel[]).map((lbl) => {
              const conf = LABEL_CONFIG[lbl];
              return (
                <button
                  key={lbl}
                  type="button"
                  onClick={() => addSpan(lbl)}
                  className={`px-2.5 py-1 rounded font-bold text-xs border transition ${conf.bg} ${conf.text} ${conf.border} hover:scale-105`}
                >
                  {lbl}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setDraftSelection(null)}
              className="p-1 rounded text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Abstract Text Rendering Container */}
      <div
        ref={textRef}
        onMouseUp={handleMouseUp}
        className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 leading-relaxed text-slate-200 text-sm select-text font-sans font-normal"
      >
        {renderHighlightedText(abstractText, sortedSpans)}
      </div>

      {/* Active Spans List */}
      {spans.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-slate-800">
          <div className="text-[11px] font-mono text-slate-400">Extracted & Verified Spans:</div>
          <div className="flex flex-wrap gap-2">
            {spans.map((span, idx) => {
              const conf = LABEL_CONFIG[span.label];
              return (
                <span
                  key={`${span.label}-${span.start_cp}-${span.end_cp}`}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border font-mono ${conf.bg} ${conf.text} ${conf.border}`}
                >
                  <span className="font-bold">{span.label}</span>
                  <span className="text-slate-300 max-w-xs truncate">&quot;{span.quote}&quot;</span>
                  <span className="text-[10px] text-slate-500 font-mono">[{span.start_cp}:{span.end_cp}]</span>
                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => removeSpan(idx)}
                      className="ml-1 hover:text-white transition"
                    >
                      ✕
                    </button>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

function renderHighlightedText(text: string, spans: PicoSpan[]): React.ReactNode {
  if (spans.length === 0) {
    return text;
  }

  // Segment the text into plain and highlighted pieces based on half-open code-point ranges
  const codePoints = Array.from(text);
  const elements: React.ReactNode[] = [];
  let currentCp = 0;

  for (const span of spans) {
    if (span.start_cp > currentCp) {
      elements.push(codePoints.slice(currentCp, span.start_cp).join(""));
    }
    const conf = LABEL_CONFIG[span.label];
    const spanText = codePoints.slice(span.start_cp, span.end_cp).join("");
    elements.push(
      <mark
        key={`span-${span.start_cp}-${span.end_cp}-${span.label}`}
        className={`px-1 rounded font-medium ${conf.highlight}`}
        title={`${conf.name} [${span.start_cp}:${span.end_cp}]`}
      >
        {spanText}
      </mark>
    );
    currentCp = Math.max(currentCp, span.end_cp);
  }

  if (currentCp < codePoints.length) {
    elements.push(codePoints.slice(currentCp).join(""));
  }

  return <>{elements}</>;
}
