import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { ApiError, request } from '../../api/client';
import type {
  Evidence,
  ExplorerPage,
  ExplorerSearch,
  GraphNode,
  PreparedExplorerContext,
  Source,
} from '../../api/types';
import { safeSourceUrl } from '../sources/SourceCards';

type NodeDetail = { graph_version: string; node: GraphNode; context_ref: string };
type DocumentDetail = { graph_version: string; source: Source; nodes: GraphNode[] };

export function StandaloneExplorer({
  runId,
  conversationId,
  onContext,
}: {
  runId: string | null;
  conversationId: string | null;
  onContext: (context: PreparedExplorerContext | null) => void;
}) {
  const [scope, setScope] = useState<'published' | 'run'>('published');
  const [query, setQuery] = useState('');
  const [searchedQuery, setSearchedQuery] = useState('');
  const [version, setVersion] = useState<string | null>(null);
  const [results, setResults] = useState<ExplorerSearch | null>(null);
  const [graph, setGraph] = useState<ExplorerPage | null>(null);
  const [node, setNode] = useState<NodeDetail | null>(null);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [prepared, setPrepared] = useState<NodeDetail | null>(null);
  const [status, setStatus] = useState('');
  const [panel, setPanel] = useState<'document' | 'graph'>('document');
  const [scale, setScale] = useState(1),
    [pan, setPan] = useState({ x: 0, y: 0 });
  const epoch = useRef(0),
    nodeRequest = useRef(0),
    documentRequest = useRef(0),
    evidenceRequest = useRef(0),
    neighborRequest = useRef(0);
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const previousRun = useRef(runId);
  const previousConversation = useRef(conversationId);
  function reset() {
    epoch.current++;
    nodeRequest.current++;
    documentRequest.current++;
    evidenceRequest.current++;
    neighborRequest.current++;
    setVersion(null);
    setResults(null);
    setGraph(null);
    setNode(null);
    setDocument(null);
    setEvidence(null);
    setPrepared(null);
    onContext(null);
    setStatus('');
    setScale(1);
    setPan({ x: 0, y: 0 });
  }
  useEffect(() => {
    if (previousRun.current !== runId) {
      previousRun.current = runId;
      if (scope === 'run') reset();
    }
  });
  useEffect(() => {
    if (previousConversation.current !== conversationId) {
      previousConversation.current = conversationId;
      setPrepared(null);
      onContext(null);
    }
  }, [conversationId, onContext]);
  useEffect(
    () => () => {
      epoch.current++;
    },
    [],
  );
  function params(pinned: string | null, extra: Record<string, string> = {}) {
    const values = new URLSearchParams({ scope, ...extra });
    if (scope === 'run' && runId) values.set('run_id', runId);
    if (pinned) values.set('graph_version', pinned);
    return values.toString();
  }
  function failed(cause: unknown) {
    if (cause instanceof ApiError && cause.status === 409) {
      reset();
      setStatus('Версия графа устарела. Выполните поиск снова.');
    } else if (cause instanceof ApiError && cause.status === 404)
      setStatus('Объект недоступен в выбранной области. Выберите другой результат.');
    else if (cause instanceof ApiError && cause.status === 503)
      setStatus('Граф временно недоступен. Повторите запрос позже.');
    else if (!(cause instanceof ApiError && cause.status === 401))
      setStatus('Не удалось загрузить данные. Повторите запрос.');
  }
  function checkVersion(received: string, expected: string) {
    if (received !== expected) throw new ApiError(409, 'GRAPH_VERSION_CONFLICT');
  }
  async function search(event: FormEvent, cursor?: string) {
    event.preventDefault();
    if (scope === 'run' && !runId) {
      setStatus('Выберите анализ в диалоге.');
      return;
    }
    const token = ++epoch.current;
    nodeRequest.current++;
    documentRequest.current++;
    evidenceRequest.current++;
    neighborRequest.current++;
    if (!cursor) {
      setResults(null);
      setGraph(null);
      setNode(null);
      setDocument(null);
      setEvidence(null);
      setPrepared(null);
      onContext(null);
    }
    setStatus('Поиск…');
    try {
      const page = await request<ExplorerSearch>(
        `/api/v1/explorer/search?${params(version, { q: cursor ? searchedQuery : query, limit: '20', ...(cursor ? { cursor } : {}) })}`,
      );
      if (token !== epoch.current) return;
      if (version) checkVersion(page.graph_version, version);
      setVersion(page.graph_version);
      if (!cursor) setSearchedQuery(query);
      setResults((old) =>
        cursor && old
          ? {
              ...page,
              nodes: [...old.nodes, ...page.nodes],
              documents: [...old.documents, ...page.documents],
            }
          : page,
      );
      setStatus(
        page.nodes.length || page.documents.length ? '' : 'Ничего не найдено. Измените запрос.',
      );
    } catch (cause) {
      if (token === epoch.current) failed(cause);
    }
  }
  async function selectNode(id: string) {
    if (!version) return;
    if (prepared && prepared.node.id !== id) {
      setPrepared(null);
      onContext(null);
    }
    const token = epoch.current,
      serial = ++nodeRequest.current;
    neighborRequest.current++;
    setNode(null);
    setStatus('Загружаем вершину…');
    try {
      const value = await request<NodeDetail>(
        `/api/v1/explorer/nodes/${encodeURIComponent(id)}?${params(version)}`,
      );
      if (token !== epoch.current || serial !== nodeRequest.current) return;
      if (value.node.id !== id) throw new ApiError(404, 'NOT_FOUND');
      checkVersion(value.graph_version, version);
      setNode(value);
      setStatus('');
      setGraph((old) =>
        old
          ? {
              ...old,
              next_cursor: null,
              nodes: old.nodes.some((n) => n.id === value.node.id)
                ? old.nodes
                : [...old.nodes, value.node],
            }
          : {
              graph_version: version,
              nodes: [value.node],
              edges: [],
              next_cursor: null,
              truncated: false,
            },
      );
    } catch (cause) {
      if (token === epoch.current && serial === nodeRequest.current) failed(cause);
    }
  }
  async function neighbors(cursor?: string) {
    if (!version || !node) return;
    const token = epoch.current,
      serial = ++neighborRequest.current,
      id = node.node.id;
    setStatus('Загружаем соседей…');
    try {
      const page = await request<ExplorerPage>(
        `/api/v1/explorer/nodes/${encodeURIComponent(id)}/neighbors?${params(version, { limit: '20', ...(cursor ? { cursor } : {}) })}`,
      );
      if (token !== epoch.current || serial !== neighborRequest.current) return;
      checkVersion(page.graph_version, version);
      setGraph((old) => ({
        ...page,
        nodes: [
          ...(old?.nodes ?? [node.node]),
          ...page.nodes.filter((n) => !(old?.nodes ?? [node.node]).some((x) => x.id === n.id)),
        ],
        edges: [
          ...(old?.edges ?? []),
          ...page.edges.filter((e) => !old?.edges.some((x) => x.id === e.id)),
        ],
      }));
      setStatus(page.edges.length ? '' : 'У этой вершины нет соседей.');
    } catch (cause) {
      if (token === epoch.current && serial === neighborRequest.current) failed(cause);
    }
  }
  async function openDocument(source: Source) {
    if (!version) return;
    const token = epoch.current,
      serial = ++documentRequest.current;
    evidenceRequest.current++;
    setDocument(null);
    setEvidence(null);
    setPanel('document');
    setStatus('Открываем документ…');
    try {
      const value = await request<DocumentDetail>(
        `/api/v1/explorer/documents/${encodeURIComponent(source.document_id)}?${params(version, { revision_id: source.revision_id })}`,
      );
      if (token !== epoch.current || serial !== documentRequest.current) return;
      if (
        value.source.document_id !== source.document_id ||
        value.source.revision_id !== source.revision_id
      )
        throw new ApiError(404, 'NOT_FOUND');
      checkVersion(value.graph_version, version);
      setDocument(value);
      setStatus('');
      setGraph((old) => ({
        graph_version: version,
        nodes: [
          ...(old?.nodes ?? []),
          ...value.nodes.filter((n) => !old?.nodes.some((x) => x.id === n.id)),
        ],
        edges: old?.edges ?? [],
        next_cursor: old?.next_cursor ?? null,
        truncated: old?.truncated ?? false,
      }));
    } catch (cause) {
      if (token === epoch.current && serial === documentRequest.current) failed(cause);
    }
  }
  async function openEvidence(id: string) {
    if (!version) return;
    const token = epoch.current,
      serial = ++evidenceRequest.current;
    setEvidence(null);
    setPanel('document');
    setStatus('Открываем фрагмент…');
    try {
      const value = await request<Evidence>(
        `/api/v1/explorer/evidence/${encodeURIComponent(id)}?${params(version)}`,
      );
      if (token !== epoch.current || serial !== evidenceRequest.current) return;
      if (value.evidence_id !== id) throw new ApiError(404, 'NOT_FOUND');
      setEvidence(value);
      setStatus('');
    } catch (cause) {
      if (token === epoch.current && serial === evidenceRequest.current) failed(cause);
    }
  }
  const positions = useMemo(
    () =>
      (graph?.nodes ?? []).map((item, i, all) => {
        const angle = (i / Math.max(all.length, 1)) * 2 * Math.PI - Math.PI / 2;
        return {
          item,
          x: 300 + Math.cos(angle) * (all.length === 1 ? 0 : 210),
          y: 180 + Math.sin(angle) * (all.length === 1 ? 0 : 130),
        };
      }),
    [graph],
  );
  const byId = new Map(positions.map((item) => [item.item.id, item]));
  const url = document && safeSourceUrl(document.source.url);
  return (
    <section className="standalone-explorer" aria-label="Обзор графа знаний">
      <div className="explorer-mobile-tabs" aria-label="Панель Explorer">
        <button aria-pressed={panel === 'document'} onClick={() => setPanel('document')}>
          Документ и поиск
        </button>
        <button aria-pressed={panel === 'graph'} onClick={() => setPanel('graph')}>
          Граф
        </button>
      </div>
      {status && (
        <p className="notice explorer-status" role="status">
          {status}
        </p>
      )}
      <div className={`explorer-document ${panel !== 'document' ? 'mobile-hidden' : ''}`}>
        <span className="eyebrow">Исследование связей</span>
        <h2>Поиск по графу знаний</h2>
        <label className="explorer-scope">
          Область{' '}
          <select
            value={scope}
            onChange={(e) => {
              reset();
              setScope(e.target.value as 'published' | 'run');
            }}
          >
            <option value="published">Опубликованный граф</option>
            <option value="run" disabled={!runId}>
              Текущий анализ
            </option>
          </select>
        </label>
        {version && <p className="explorer-version">Версия графа: {version}</p>}
        <form className="explorer-search" onSubmit={(e) => void search(e)}>
          <label htmlFor="explorer-query">Сущность или документ</label>
          <div>
            <input id="explorer-query" value={query} onChange={(e) => setQuery(e.target.value)} />
            <button type="submit">Найти</button>
          </div>
        </form>
        {results && (
          <div className="explorer-results">
            <h3>Результаты</h3>
            {results.nodes.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  void selectNode(item.id);
                  setPanel('graph');
                }}
              >
                {item.label} <small>{item.type}</small>
              </button>
            ))}
            {results.documents.map((item) => (
              <button
                key={`${item.document_id}:${item.revision_id}`}
                onClick={() => void openDocument(item)}
              >
                {item.title} <small>{item.kind}</small>
              </button>
            ))}
            {results.truncated && <p>Показана часть результатов.</p>}
            {results.next_cursor && (
              <button onClick={(e) => void search(e, results.next_cursor!)}>Показать ещё</button>
            )}
          </div>
        )}
        {document && (
          <article className="explorer-source">
            <span className="eyebrow">{document.source.kind}</span>
            <h3>{document.source.title}</h3>
            <p>Ревизия: {document.source.revision_id}</p>
            {url && (
              <a href={url} target="_blank" rel="noopener noreferrer">
                Открыть источник ↗
              </a>
            )}
            <div>
              {document.source.evidence_ids.map((id, i) => (
                <button className="text-button" key={id} onClick={() => void openEvidence(id)}>
                  Фрагмент {i + 1}
                </button>
              ))}
            </div>
            {document.nodes.map((item) => (
              <button
                className="text-button"
                key={item.id}
                onClick={() => {
                  void selectNode(item.id);
                  setPanel('graph');
                }}
              >
                Вершина: {item.label}
              </button>
            ))}
          </article>
        )}
        {evidence && (
          <article className="explorer-source">
            <span className="eyebrow">{evidence.section}</span>
            <blockquote>{evidence.quoted_span}</blockquote>
            <p>
              Ревизия {evidence.revision_id} · Символы {evidence.span_start}–{evidence.span_end}
            </p>
          </article>
        )}
      </div>
      <div className={`explorer-graph ${panel !== 'graph' ? 'mobile-hidden' : ''}`}>
        <div className="graph-heading">
          <div>
            <span className="eyebrow">Карта связей</span>
            <p>Выберите вершину и раскройте её соседей</p>
          </div>
          <div className="graph-zoom">
            <button
              aria-label="Уменьшить граф"
              onClick={() => setScale((v) => Math.max(0.65, v - 0.15))}
            >
              −
            </button>
            <button
              aria-label="Увеличить граф"
              onClick={() => setScale((v) => Math.min(1.8, v + 0.15))}
            >
              +
            </button>
          </div>
        </div>
        <p className="explorer-legend">
          <span>━ Фактическая связь</span> <span>┄ Семантическая связь</span>
        </p>
        {!positions.length ? (
          <p className="muted">Результаты появятся после выбора вершины.</p>
        ) : (
          <>
            <svg
              className="graph-canvas explorer-canvas"
              viewBox="0 0 600 360"
              aria-label="Граф знаний"
              role="group"
              onPointerDown={(e) => {
                if (e.target === e.currentTarget) {
                  e.currentTarget.setPointerCapture(e.pointerId);
                  drag.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
                }
              }}
              onPointerMove={(e) => {
                if (drag.current) {
                  const box = e.currentTarget.getBoundingClientRect();
                  setPan({
                    x: drag.current.panX + ((e.clientX - drag.current.x) * 600) / box.width,
                    y: drag.current.panY + ((e.clientY - drag.current.y) * 360) / box.height,
                  });
                }
              }}
              onPointerUp={() => {
                drag.current = null;
              }}
              onPointerCancel={() => {
                drag.current = null;
              }}
            >
              <g
                transform={`translate(${300 * (1 - scale) + pan.x} ${180 * (1 - scale) + pan.y}) scale(${scale})`}
              >
                {graph?.edges.map((edge) => {
                  const a = byId.get(edge.source),
                    b = byId.get(edge.target);
                  return a && b ? (
                    <line
                      key={edge.id}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      className={`graph-edge ${edge.kind}`}
                    >
                      <title>
                        {edge.kind === 'factual' ? 'Фактическая' : 'Семантическая'}: {edge.type}
                      </title>
                    </line>
                  ) : null;
                })}
                {positions.map(({ item, x, y }) => (
                  <g
                    key={item.id}
                    className="graph-node"
                    role="button"
                    tabIndex={0}
                    aria-label={item.label}
                    onClick={() => void selectNode(item.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        void selectNode(item.id);
                      }
                    }}
                  >
                    <circle
                      cx={x}
                      cy={y}
                      r="24"
                      fill={node?.node.id === item.id ? '#493c82' : '#187b78'}
                    />
                    <text x={x} y={y + 4}>
                      {item.label.length > 20 ? `${item.label.slice(0, 18)}…` : item.label}
                    </text>
                  </g>
                ))}
              </g>
            </svg>
            <div className="explorer-node-list">
              {positions.map(({ item }) => (
                <button key={item.id} onClick={() => void selectNode(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>
          </>
        )}
        {node && (
          <aside className="graph-details">
            <span className="eyebrow">{node.node.type}</span>
            <strong>{node.node.label}</strong>
            <div className="graph-detail-actions">
              <button className="text-button" onClick={() => void neighbors()}>
                Раскрыть соседей
              </button>
              {graph?.next_cursor && (
                <button className="text-button" onClick={() => void neighbors(graph.next_cursor!)}>
                  Ещё соседи
                </button>
              )}
              <button
                className="text-button"
                onClick={() => {
                  setPrepared(node);
                  onContext({ ref: node.context_ref, label: node.node.label });
                }}
              >
                Подготовить контекст
              </button>
              {node.node.evidence_ids.map((id, i) => (
                <button className="text-button" key={id} onClick={() => void openEvidence(id)}>
                  Открыть цитату {i + 1}
                </button>
              ))}
              {node.node.document_id && node.node.revision_id && (
                <button
                  className="text-button"
                  onClick={() =>
                    void openDocument({
                      document_id: node.node.document_id!,
                      revision_id: node.node.revision_id!,
                      title: node.node.label,
                      kind: node.node.type,
                      url: '',
                      evidence_ids: node.node.evidence_ids,
                    })
                  }
                >
                  Открыть документ
                </button>
              )}
            </div>
            {prepared?.node.id === node.node.id && (
              <p>Контекст подготовлен для дальнейшего использования.</p>
            )}
          </aside>
        )}
        {graph?.truncated && <p className="graph-note">Показана часть связей.</p>}
        {graph?.edges.map((edge) => (
          <div className="explorer-edge" key={edge.id}>
            <span>
              {edge.kind === 'factual' ? 'Фактическая' : 'Семантическая'} · {edge.type}
            </span>
            {edge.kind === 'factual' &&
              edge.evidence_ids.map((id, i) => (
                <button className="text-button" key={id} onClick={() => void openEvidence(id)}>
                  Цитата {i + 1}
                </button>
              ))}
          </div>
        ))}
      </div>
    </section>
  );
}
