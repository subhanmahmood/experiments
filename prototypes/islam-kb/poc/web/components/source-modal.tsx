"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Source } from "@/lib/rag/types";

interface SourceModalProps {
  source: Source | null;
  onClose: () => void;
}

export function SourceModal({ source, onClose }: SourceModalProps) {
  return (
    <Dialog open={!!source} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>{source?.book}</DialogTitle>
          <DialogDescription>
            Page {source?.page} | Relevance:{" "}
            {((source?.score || 0) * 100).toFixed(1)}%
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 p-4 bg-muted rounded-lg">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {source?.text}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
