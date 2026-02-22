import React, { useState } from "react";
import { Maximize2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../ui/dialog";

interface ChartEnlargeWrapperProps {
  title: string;
  children: React.ReactNode;
}

export function ChartEnlargeWrapper({
  title,
  children,
}: ChartEnlargeWrapperProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setOpen(true)}
          className="absolute z-10 rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          style={{ top: -36, right: 0 }}
          aria-label={`Enlarge ${title}`}
        >
          <Maximize2 className="size-4" />
        </button>
        {children}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[90vw] h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0">{open && children}</div>
        </DialogContent>
      </Dialog>
    </>
  );
}
