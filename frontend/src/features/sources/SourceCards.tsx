import type { Evidence, Source } from '../../api/types';

const hosts = new Set(['worldwide.espacenet.com', 'openalex.org', 'doi.org', 'patents.google.com']);
export function safeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' &&
      hosts.has(url.hostname) &&
      !url.username &&
      !url.password &&
      (!url.port || url.port === '443')
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function SourceCards({
  sources,
  active,
  evidence,
  loading,
  onEvidence,
  onExplain,
}: {
  sources: Source[];
  active: string | null;
  evidence: Evidence | null;
  loading: boolean;
  onEvidence: (source: Source, evidence: string) => void;
  onExplain: (source: Source) => void;
}) {
  return (
    <section className="sources-panel" aria-label="Источники анализа">
      <div className="section-heading">
        <span className="eyebrow">Первоисточники</span>
        <span className="counter">{sources.length}</span>
      </div>
      {sources.length === 0 ? (
        <p className="empty-sources">
          Здесь появятся публикации и патенты, на которые опирается ответ.
        </p>
      ) : (
        sources.map((source, index) => {
          const url = safeSourceUrl(source.url);
          const selected = source.evidence_ids.includes(active ?? '');
          return (
            <article
              className={`source-card ${selected ? 'selected' : ''}`}
              key={source.document_id}
              id={`source-${source.document_id}`}
              tabIndex={-1}
            >
              <div className="source-meta">
                <span>{String(index + 1).padStart(2, '0')}</span>
                <span>{source.kind === 'patent' ? 'Патент' : 'Публикация'}</span>
                {source.publication_date && <time>{source.publication_date.slice(0, 10)}</time>}
              </div>
              <h3>{source.title}</h3>
              <div className="source-actions">
                {source.evidence_ids.map((id, number) => (
                  <button
                    type="button"
                    className="text-button"
                    key={id}
                    onClick={() => onEvidence(source, id)}
                  >
                    Фрагмент {number + 1}
                  </button>
                ))}
                {url && (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    Открыть источник ↗
                  </a>
                )}
              </div>
              {selected && (
                <div className="evidence-detail" aria-live="polite">
                  {loading ? (
                    <p>Загружаем фрагмент…</p>
                  ) : evidence?.evidence_id === active ? (
                    <>
                      <span className="eyebrow">
                        {evidence.section === 'abstract' ? 'Аннотация' : evidence.section}
                      </span>
                      <blockquote>{evidence.quoted_span}</blockquote>
                      <span className="evidence-offset">
                        Символы {evidence.span_start}–{evidence.span_end}
                      </span>
                    </>
                  ) : (
                    <p>Фрагмент не загружен.</p>
                  )}
                </div>
              )}
              <button type="button" className="explain-button" onClick={() => onExplain(source)}>
                Объяснить этот источник <span>→</span>
              </button>
            </article>
          );
        })
      )}
    </section>
  );
}
