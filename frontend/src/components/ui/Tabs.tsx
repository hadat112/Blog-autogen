export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (value: T) => void; items: Array<{ value: T; label: string }> }) {
  return (
    <div role="tablist" className="inline-flex rounded-lg border border-border-default bg-surface-subtle p-1">
      {items.map(item => <button key={item.value} role="tab" aria-selected={value === item.value} type="button" onClick={() => onChange(item.value)} className={`cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${value === item.value ? 'bg-surface text-content-primary shadow-sm' : 'text-content-secondary hover:text-content-primary'}`}>{item.label}</button>)}
    </div>
  );
}
