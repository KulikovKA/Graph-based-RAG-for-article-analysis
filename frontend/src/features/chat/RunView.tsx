import { useEffect, useState } from 'react';
import type { Claim, Run } from '../../api/types';
import type { Connection } from './useRun';
import type { RunState } from './runState';
import { terminal } from './runState';

const stages: Record<string, string> = {
  accepted: 'В очереди',
  planning: 'Уточняем признаки идеи',
  retrieving: 'Ищем публикации и патенты',
  reranking: 'Выбираем релевантные источники',
  analyzing: 'Анализ продолжается',
  verification: 'Проверяем выводы и цитаты',
  completed: 'Анализ завершён',
  failed: 'Анализ не завершён',
  cancelled: 'Анализ отменён',
};
function Claims({ items, onCitation }: { items: Claim[]; onCitation: (id: string) => void }) {
  return (
    <>
      {items.map((claim, index) => (
        <p key={index}>
          {claim.text}{' '}
          <span className="citations">
            {claim.evidence_ids.map((id, n) => (
              <button
                className="citation"
                key={id}
                onClick={() => onCitation(id)}
                aria-label={`Открыть цитату ${n + 1}`}
              >
                [{n + 1}]
              </button>
            ))}
          </span>
        </p>
      ))}
    </>
  );
}

export function RunView({
  state,
  connection = 'closed',
  onCancel,
  onCitation,
  onShowAll,
}: {
  state: RunState;
  connection?: Connection;
  onCancel?: () => void;
  onCitation: (id: string) => void;
  onShowAll?: () => void;
}) {
  const run = state.run;
  const [now, setNow] = useState(Date.now());
  const [shown, setShown] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const [reduced, setReduced] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  const recorded = useState(() => new Set<string>())[0];
  useEffect(() => {
    const keys: string[] = [];
    if (!terminal(run)) keys.push('first_progress_display');
    if (state.verified && run.public_analysis) keys.push('first_summary_display');
    if (display && state.chunks.length) keys.push('first_delta_display');
    for (const key of keys) {
      const name = `analysis:${run.id}:${key}`;
      if (recorded.has(name)) continue;
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          if (!recorded.has(name)) {
            recorded.add(name);
            performance.mark(name);
          }
        }),
      );
    }
  });
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => setReduced(query.matches);
    query.addEventListener('change', change);
    return () => query.removeEventListener('change', change);
  }, []);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    setShown(0);
    setShowAll(false);
  }, [run.id]);
  useEffect(() => {
    if (reduced || showAll || terminal(run)) return;
    const timer = setInterval(
      () => setShown((value) => Math.min(value + 32, Array.from(state.text).length)),
      24,
    );
    return () => clearInterval(timer);
  }, [state.text, reduced, showAll, run]);
  const display =
    reduced || showAll || terminal(run)
      ? state.text
      : Array.from(state.text).slice(0, shown).join('');
  const progress = 'stage' in run.progress ? run.progress : null;
  const seconds = Math.max(
    0,
    Math.floor((now - Date.parse(progress?.stage_started_at ?? run.created_at)) / 1000),
  );
  const countNames: Record<string, string> = {
    feature_count: 'признаков',
    candidate_count: 'кандидатов',
    selected_document_count: 'источников',
  };
  const counts = Object.entries(progress?.counts ?? {}).filter(
    ([, value]) => typeof value === 'number',
  );
  const outcomeNames: Partial<Record<NonNullable<Run['outcome']>, string>> = {
    safe_fallback: 'Сокращённый ответ',
    no_evidence: 'Подтверждений не найдено',
    clarification: 'Нужно уточнение',
  };
  return (
    <article className="run-view" data-run={run.id}>
      <div className="analysis-label">
        <span className="small-mark">✧</span>
        <span>Анализ</span>
        {run.coverage.historical && <span className="badge">По сохранённым источникам</span>}
      </div>
      {!terminal(run) && (
        <div className="progress-card" aria-live="polite">
          <div className="progress-top">
            <span className="status-dot" />
            <strong>
              {state.verified
                ? 'Результат проверен — получаем ответ'
                : (stages[run.stage] ?? 'Анализ продолжается')}
            </strong>
            <span className="elapsed">
              {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
            </span>
          </div>
          <p>
            Поиск и проверка могут занять несколько минут. Результат появится после проверки цитат.
          </p>
          {counts.length > 0 && (
            <div className="counts">
              {counts.map(([key, value]) => (
                <span key={key}>
                  <b>{value}</b> {countNames[key]}
                </span>
              ))}
            </div>
          )}
          {progress && progress.attempt > 1 && <p>Повторная попытка {progress.attempt}</p>}
          <div className="progress-actions">
            <span className="connection">
              {connection === 'reconnecting'
                ? 'Восстанавливаем соединение…'
                : connection === 'offline'
                  ? 'Соединение потеряно'
                  : 'Статусы обновляются автоматически'}
            </span>
            {onCancel && (
              <button className="text-button" onClick={onCancel}>
                Отменить анализ
              </button>
            )}
          </div>
        </div>
      )}
      {run.status === 'failed' && (
        <p className="notice error">Не удалось завершить анализ. Отправьте запрос ещё раз.</p>
      )}
      {run.status === 'cancelled' && (
        <p className="notice">Анализ отменён. Можно уточнить идею и начать новый запрос.</p>
      )}
      {run.coverage.partial && (
        <p className="notice warning">
          Неполное покрытие: часть источников недоступна. Выводы ограничены найденными материалами.
        </p>
      )}
      {run.outcome && outcomeNames[run.outcome] && (
        <p className="notice">
          {outcomeNames[run.outcome]}
          {run.outcome === 'safe_fallback'
            ? ': показаны проверенные выдержки без полного сравнения.'
            : '.'}
        </p>
      )}
      {state.verified && run.public_analysis && (
        <details className="public-analysis">
          <summary>
            Ход анализа <span>Проверено ✓</span>
          </summary>
          <div>
            <Claims items={run.public_analysis.items} onCitation={onCitation} />
            {run.public_analysis.limitations.map((item) => (
              <p className="muted" key={item.code}>
                {item.message}
              </p>
            ))}
            {run.public_analysis.items.length === 0 && (
              <p className="muted">Фактические выводы для этого результата отсутствуют.</p>
            )}
          </div>
        </details>
      )}
      {display && (
        <div className="answer-text" data-testid="answer-text">
          {display}
        </div>
      )}
      {state.text && !terminal(run) && !showAll && !reduced && (
        <button
          className="text-button show-all"
          onClick={() => {
            setShowAll(true);
            onShowAll?.();
          }}
        >
          Показать целиком
        </button>
      )}
      {run.status === 'completed' && run.answer && (
        <div className="structured-answer">
          {!run.answer_presentation && (
            <>
              <Claims items={run.answer.summary} onCitation={onCitation} />
              {run.answer.matches.length > 0 && (
                <>
                  <h3>Совпадения</h3>
                  <Claims
                    items={run.answer.matches.flatMap((item) => item.claims)}
                    onCitation={onCitation}
                  />
                </>
              )}
              {run.answer.differences.length > 0 && (
                <>
                  <h3>Отличия</h3>
                  <Claims
                    items={run.answer.differences.flatMap((item) => item.claims)}
                    onCitation={onCitation}
                  />
                </>
              )}
            </>
          )}
          <div className="answer-citations">
            {Array.from(
              new Set(
                [
                  ...run.answer.summary,
                  ...run.answer.matches.flatMap((x) => x.claims),
                  ...run.answer.differences.flatMap((x) => x.claims),
                ].flatMap((x) => x.evidence_ids),
              ),
            ).map((id, n) => (
              <button className="citation" key={id} onClick={() => onCitation(id)}>
                Цитата {n + 1} ↗
              </button>
            ))}
          </div>
          {run.answer.limitations.map((item) => (
            <p className="answer-limitation" key={item.code}>
              {item.message}
            </p>
          ))}
        </div>
      )}
      {terminal(run) && (
        <div className="result-footer">
          {run.status === 'completed' ? 'Ответ сохранён' : stages[run.status]}
          <span>
            {run.sources.length} {run.sources.length === 1 ? 'источник' : 'источников'}
          </span>
        </div>
      )}
    </article>
  );
}
