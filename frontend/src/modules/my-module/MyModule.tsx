import { Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Item {
  id: string;
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export default function MyModule() {
  const { t } = useTranslation();
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const url = new URL('/api/v1/my_module/', window.location.origin);
    fetch(url.toString())
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return (await res.json()) as Item[];
      })
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Sparkles className="h-6 w-6" />
        <h1 className="text-2xl font-bold">
          {t('mymodule.heading', { defaultValue: 'My Module' })}
        </h1>
      </div>
      <p className="text-muted-foreground">
        {t('mymodule.subtitle', { defaultValue: 'Manage items belonging to a project.' })}
      </p>

      {error && <div className="text-destructive">{error}</div>}

      {items === null && !error && <div>Loading…</div>}

      {items !== null && items.length === 0 && (
        <div className="text-muted-foreground">
          {t('mymodule.empty', { defaultValue: 'No items yet.' })}
        </div>
      )}

      {items !== null && items.length > 0 && (
        <ul className="divide-y">
          {items.map((item) => (
            <li key={item.id} className="py-2">
              <div className="font-medium">{item.name}</div>
              {item.description && (
                <div className="text-sm text-muted-foreground">{item.description}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
