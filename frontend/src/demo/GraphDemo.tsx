import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from '../api/client';
import type { GraphNode, GraphEdge, GraphView, Run } from '../api/types';
import { GraphExplorer } from '../features/graph/GraphExplorer';
import '../style.css';

// Изолированная страница: все данные вымышлены, обращения к серверу не нужны.
const node = (id: string, type: string, label: string, evidence_ids: string[] = []): GraphNode =>
  ({ id, type, label, evidence_ids });
const edge = (source: string, target: string, type: string): GraphEdge =>
  ({ id: `${source}:${target}`, source, target, type, evidence_ids: [] });
const nodes = [
  node('idea', 'Idea', 'Охлаждение батареи'),
  node('f1', 'IdeaFeature', 'Датчики температуры'),
  node('paper1', 'ScientificWork', 'Обратная связь', ['e1']),
  node('patent1', 'Patent', 'Жидкостные каналы', ['e2']),
  node('f2', 'IdeaFeature', 'Раздельные контуры'),
  node('paper2', 'ScientificWork', 'Баланс температур', ['e3']),
  node('patent2', 'Patent', 'Управление насосом', ['e4']),
  node('f3', 'IdeaFeature', 'Регулировка потока'),
];
const edges = [
  ...['f1', 'f2', 'f3'].map((id) => edge('idea', id, 'HAS_FEATURE')),
  edge('f1', 'paper1', 'MATCHES'), edge('f1', 'paper2', 'MATCHES'),
  edge('f2', 'patent1', 'MATCHES'), edge('f2', 'paper2', 'MATCHES'),
  edge('f3', 'patent2', 'MATCHES'), edge('f3', 'paper1', 'MATCHES'),
];
const details: Record<string, { labels: string[]; evidence: string; quote: string }> = {
  paper1: { labels: ['Измерение каждые 100 мс', 'Порог включения 35 °C'], evidence: 'e1', quote: 'Тестовая цитата: контроллер измеряет температуру ячеек каждые 100 мс и включает охлаждение при превышении 35 °C.' },
  patent1: { labels: ['Канал для каждого модуля', 'Параллельная циркуляция'], evidence: 'e2', quote: 'Тестовая цитата: каждый модуль соединён с отдельным жидкостным каналом. Контуры работают параллельно.' },
  paper2: { labels: ['Разница температур < 3 °C', 'Сравнение соседних ячеек'], evidence: 'e3', quote: 'Тестовая цитата: система сравнивает соседние ячейки и поддерживает разницу температур менее 3 °C.' },
  patent2: { labels: ['Изменяемая скорость насоса', 'Обратная связь по расходу'], evidence: 'e4', quote: 'Тестовая цитата: скорость насоса изменяется по данным датчика расхода и температуры батареи.' },
};
const view = (viewNodes: GraphNode[], viewEdges: GraphEdge[]): GraphView => ({
  run_id: 'graph-demo', graph_version: 'demo-v1', nodes: viewNodes, edges: viewEdges,
  next_cursor: null, truncated: false,
});
api.graph = async () => structuredClone(view(nodes, edges));
api.graphNeighbors = async (_run, id) => {
  const detail = details[id];
  if (!detail) return view([], []);
  const neighbors = detail.labels.map((label, index) =>
    node(`${id}-technical-${index}`, 'TechnicalFeature', label, [detail.evidence]));
  return view(neighbors, neighbors.map((item) => edge(id, item.id, 'DISCLOSES_FEATURE')));
};
const run: Run = {
  id: 'graph-demo', status: 'completed', stage: 'completed', progress: {},
  idea_version_id: 'demo-idea', source_run_id: null, outcome: 'analysis',
  answer: null, public_analysis: null, answer_presentation: null, sources: [],
  coverage: { sources: [], channels: [], partial: false, historical: false },
  graph_url: '/demo/graph', created_at: '2026-10-03T12:00:00Z',
  completed_at: '2026-10-03T12:00:00Z', error_code: null,
};

function GraphDemo() {
  const [reset, setReset] = useState(0);
  const [citation, setCitation] = useState<string | null>(null);
  return <main style={{ maxWidth: 1120, margin: '32px auto', padding: '0 24px' }}>
    <span className="eyebrow">Контекст · Тестовые данные</span>
    <h1 style={{ margin: '12px 0' }}>Исследуйте граф связей</h1>
    <p>Вымышленный пример: охлаждение батареи. 8 узлов и 9 связей; у каждого источника есть ещё два признака.</p>
    <p>Тяните свободное поле мышью для перемещения. Кнопки + и − меняют масштаб.
      Нажмите узел для деталей и подсветки пути. У источников нажмите «Раскрыть один hop».</p>
    <button className="text-button" onClick={() => { setReset((value) => value + 1); setCitation(null); }}>Сбросить вид и связи</button>
    <GraphExplorer key={reset} run={run} onCitation={(id) => setCitation(id)} />
    {citation && <aside className="graph-details" aria-label="Тестовая цитата">
      <button className="graph-close" aria-label="Закрыть цитату" onClick={() => setCitation(null)}>×</button>
      <strong>Цитата из вымышленного источника</strong>
      <p>{Object.values(details).find((item) => item.evidence === citation)?.quote}</p>
    </aside>}
    <p className="muted">Фиолетовый — идея и её признаки · Синий — статья · Зелёный — патент · Серый — признак источника.</p>
  </main>;
}

createRoot(document.getElementById('root')!).render(<GraphDemo />);
