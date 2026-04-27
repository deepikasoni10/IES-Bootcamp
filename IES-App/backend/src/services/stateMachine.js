/**
 * Component 10: Filing State Machine
 * Manages valid state transitions for a filing lifecycle.
 *
 * States:
 *   preparing → draft_submitted → draft_validated → formally_submitted
 *   → accepted | rejected → disclosed
 */

export const STATES = {
  PREPARING:            'preparing',
  DRAFT_SUBMITTED:      'draft_submitted',
  DRAFT_VALIDATED:      'draft_validated',
  FORMALLY_SUBMITTED:   'formally_submitted',
  ACCEPTED:             'accepted',
  REJECTED:             'rejected',
  DISCLOSED:            'disclosed',
};

/** Allowed transitions: { fromState: [toStates] } */
const TRANSITIONS = {
  [STATES.PREPARING]:           [STATES.DRAFT_SUBMITTED],
  [STATES.DRAFT_SUBMITTED]:     [STATES.DRAFT_VALIDATED, STATES.PREPARING],  // can re-submit
  [STATES.DRAFT_VALIDATED]:     [STATES.FORMALLY_SUBMITTED, STATES.PREPARING],
  [STATES.FORMALLY_SUBMITTED]:  [STATES.ACCEPTED, STATES.REJECTED],
  [STATES.ACCEPTED]:            [STATES.DISCLOSED],
  [STATES.REJECTED]:            [STATES.PREPARING],  // allow re-submission
  [STATES.DISCLOSED]:           [],                  // terminal
};

/**
 * Validate a state transition.
 */
export function canTransition(currentState, nextState) {
  return (TRANSITIONS[currentState] || []).includes(nextState);
}

/**
 * Perform a state transition, returning updated filing object.
 * Throws if transition is invalid.
 */
export function transition(filing, nextState, metadata = {}) {
  if (!canTransition(filing.status, nextState)) {
    throw new Error(
      `Invalid transition: ${filing.status} → ${nextState}. ` +
      `Allowed: [${(TRANSITIONS[filing.status] || []).join(', ')}]`
    );
  }

  const now = new Date().toISOString();
  const updated = {
    ...filing,
    status:    nextState,
    updatedAt: now,
    history:   [...(filing.history || []), {
      from:      filing.status,
      to:        nextState,
      at:        now,
      ...metadata,
    }],
  };

  // Set specific timestamp fields
  switch (nextState) {
    case STATES.DRAFT_SUBMITTED:    updated.draftSubmittedAt    = now; break;
    case STATES.DRAFT_VALIDATED:    updated.draftValidatedAt    = now; break;
    case STATES.FORMALLY_SUBMITTED: updated.formalSubmittedAt   = now; break;
    case STATES.ACCEPTED:           updated.acceptedAt          = now; break;
    case STATES.REJECTED:           updated.rejectedAt          = now; break;
    case STATES.DISCLOSED:          updated.disclosedAt         = now; break;
  }

  return updated;
}
