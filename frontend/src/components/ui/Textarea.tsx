import * as React from 'react';
import { cn } from '../../lib/utils';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn('min-h-32 w-full resize-y rounded-md border border-[var(--input-border)] bg-[var(--input-bg)] px-3 py-2 text-sm text-[var(--input-text)] shadow-sm transition-colors placeholder:text-[var(--input-placeholder)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--input-border-focus)] disabled:opacity-50', className)}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';
