/**
 * 8-column Kanban board for the opportunity pipeline.
 *
 * Uses @dnd-kit for drag-and-drop.  When a card is dropped on a target
 * column the component asks the consumer to attempt the transition; if the
 * server rejects it (e.g. backward jump per T11-08) the consumer can show a
 * toast — the card visually snaps back because the data hasn't moved.
 */

import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import clsx from 'clsx';

import { PIPELINE_STAGES, type PipelineStage } from '../api/types';
import { OpportunityCard, type OpportunityCardData } from './OpportunityCard';
import { StageBadge } from './StageBadge';

export interface PipelineKanbanProps {
  opportunities: OpportunityCardData[];
  onCardClick?: (id: string) => void;
  /**
   * Called when the user drops a card on a column.  Return `true` from the
   * promise on success; on failure the consumer is responsible for showing
   * a toast — the card simply stays in the source column because the
   * underlying data hasn't been mutated yet (parent re-fetches on success).
   */
  onTransition: (
    opportunityId: string,
    fromStage: PipelineStage,
    toStage: PipelineStage,
  ) => Promise<boolean>;
}

const STAGE_HEADER_LABEL: Record<PipelineStage, string> = {
  identified: 'Identified',
  triaged: 'Triaged',
  qualified: 'Qualified',
  bidding: 'Bidding',
  submitted: 'Submitted',
  awarded: 'Awarded',
  lost: 'Lost',
  no_bid: 'No Bid',
};

export function PipelineKanban({
  opportunities,
  onCardClick,
  onTransition,
}: PipelineKanbanProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const opportunityId = String(active.id);
    const targetStage = String(over.id) as PipelineStage;
    const card = opportunities.find((o) => o.id === opportunityId);
    if (!card) return;
    if (card.stage === targetStage) return;
    void onTransition(opportunityId, card.stage, targetStage);
  };

  const byStage = groupByStage(opportunities);

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="grid grid-flow-col auto-cols-[minmax(220px,1fr)] gap-3 overflow-x-auto pb-3">
        {PIPELINE_STAGES.map((stage) => (
          <KanbanColumn
            key={stage}
            stage={stage}
            count={byStage[stage].length}
          >
            {byStage[stage].map((opp) => (
              <DraggableCard
                key={opp.id}
                opportunity={opp}
                onCardClick={onCardClick}
              />
            ))}
          </KanbanColumn>
        ))}
      </div>
    </DndContext>
  );
}

// ── Column ────────────────────────────────────────────────────────────────

function KanbanColumn({
  stage,
  count,
  children,
}: {
  stage: PipelineStage;
  count: number;
  children: React.ReactNode;
}) {
  const { isOver, setNodeRef } = useDroppable({ id: stage });

  return (
    <div
      ref={setNodeRef}
      className={clsx(
        'flex h-full min-h-[320px] flex-col rounded-lg border border-gray-200 bg-gray-50/50 p-2 transition',
        isOver && 'border-[#B8232C] bg-[#B8232C]/5',
      )}
      data-column={stage}
    >
      <div className="mb-2 flex items-center justify-between px-1">
        <span className="font-display text-xs font-bold uppercase tracking-widest text-gray-700">
          {STAGE_HEADER_LABEL[stage]}
        </span>
        <span className="font-mono text-[11px] text-gray-500">{count}</span>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto">{children}</div>
    </div>
  );
}

// ── Draggable wrapper ─────────────────────────────────────────────────────

function DraggableCard({
  opportunity,
  onCardClick,
}: {
  opportunity: OpportunityCardData;
  onCardClick?: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: opportunity.id,
  });

  const style: React.CSSProperties | undefined = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: isDragging ? 50 : undefined,
      }
    : undefined;

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <OpportunityCard
        opportunity={opportunity}
        onClick={onCardClick}
        draggable
        className={isDragging ? 'shadow-2xl ring-2 ring-[#B8232C]' : undefined}
      />
    </div>
  );
}

// ── Internals ─────────────────────────────────────────────────────────────

function groupByStage(opportunities: OpportunityCardData[]) {
  const out: Record<PipelineStage, OpportunityCardData[]> = {
    identified: [],
    triaged: [],
    qualified: [],
    bidding: [],
    submitted: [],
    awarded: [],
    lost: [],
    no_bid: [],
  };
  for (const o of opportunities) {
    out[o.stage].push(o);
  }
  return out;
}

// Re-export the StageBadge so consumers don't have to find it separately
// when wiring a header outside the Kanban (it's used in list views too).
export { StageBadge };
